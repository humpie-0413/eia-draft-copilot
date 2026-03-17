"""공공데이터 커넥터 기본 인터페이스.

모든 커넥터는 BaseConnector를 상속하며, fetch()와 normalize()를 구현해야 한다.
fetch()는 외부 API를 호출하여 원시 응답을 반환하고,
normalize()는 원시 응답을 EvidenceCreate 목록으로 변환한다.
"""

import asyncio
import gc
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.evidence import create_evidences_bulk
from app.crud.source_snapshot import create_snapshot
from app.models.evidence import Evidence
from app.models.source_snapshot import SourceSnapshot
from app.schemas.evidence import EvidenceCreate
from app.schemas.source_snapshot import SnapshotStatus, SourceSnapshotCreate

logger = logging.getLogger(__name__)

# 재시도 설정
MAX_RETRIES = 2          # 최대 재시도 횟수 (총 3회 시도)
RETRY_DELAY_SEC = 3.0    # 재시도 간 대기 시간 (초)

# 재시도 대상 예외 (타임아웃, 연결 오류)
_RETRYABLE_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    OSError,
)

# httpx 예외는 런타임에 확인 (httpx가 없을 수도 있는 테스트 환경 대응)
try:
    import httpx
    _RETRYABLE_EXCEPTIONS = (
        *_RETRYABLE_EXCEPTIONS,
        httpx.TimeoutException,
        httpx.ConnectError,
    )
except ImportError:
    pass


class BaseConnector(ABC):
    """공공데이터 커넥터 추상 기본 클래스."""

    # 하위 클래스에서 반드시 설정해야 하는 값
    connector_key: str = ""
    display_name: str = ""

    @abstractmethod
    async def fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        """외부 API를 호출하여 원시 응답을 반환한다.

        Args:
            params: API 요청 파라미터 (지역, 기간, 측정소 등)

        Returns:
            원시 JSON 응답 딕셔너리
        """
        ...

    @abstractmethod
    def normalize(
        self,
        raw_payload: dict[str, Any],
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        screening_only: bool = False,
    ) -> list[EvidenceCreate]:
        """원시 응답을 정규화된 EvidenceCreate 목록으로 변환한다.

        Args:
            raw_payload: fetch()에서 반환된 원시 데이터
            project_id: 대상 프로젝트 ID
            data_source_id: 데이터 소스 ID
            snapshot_id: 스냅샷 ID (증거와 원시 데이터 간 추적용)
            screening_only: True이면 스크리닝 전용 데이터로 태깅

        Returns:
            정규화된 증거 목록
        """
        ...

    async def _fetch_with_retry(self, params: dict[str, Any]) -> dict[str, Any]:
        """재시도 로직이 포함된 fetch 호출.

        타임아웃/연결 오류 시 최대 MAX_RETRIES회 재시도한다.
        ValueError, RuntimeError 등 비즈니스 오류는 즉시 전파한다.
        """
        last_exc: Exception | None = None

        for attempt in range(1 + MAX_RETRIES):
            try:
                return await self.fetch(params)
            except _RETRYABLE_EXCEPTIONS as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_SEC * (attempt + 1)
                    logger.warning(
                        "[%s] API 호출 실패 (시도 %d/%d): %s — %.1f초 후 재시도",
                        self.connector_key,
                        attempt + 1,
                        1 + MAX_RETRIES,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "[%s] API 호출 최종 실패 (%d회 시도 모두 실패): %s",
                        self.connector_key,
                        1 + MAX_RETRIES,
                        exc,
                    )
            except Exception:
                # 비즈니스 오류 (ValueError 등)는 재시도하지 않음
                raise

        # 마지막 예외를 다시 발생
        raise last_exc  # type: ignore[misc]

    async def collect(
        self,
        db: AsyncSession,
        project_id: uuid.UUID,
        data_source_id: uuid.UUID,
        params: dict[str, Any],
        screening_only: bool = False,
    ) -> tuple[SourceSnapshot, list[Evidence]]:
        """수집 전체 파이프라인: fetch → 스냅샷 저장 → normalize → 증거 저장.

        Args:
            db: 비동기 DB 세션
            project_id: 대상 프로젝트 ID
            data_source_id: 데이터 소스 ID
            params: API 요청 파라미터
            screening_only: 스크리닝 전용 데이터 여부

        Returns:
            (생성된 스냅샷, 생성된 증거 목록) 튜플
        """
        # 1) 외부 API 호출 (재시도 포함)
        try:
            raw_payload = await self._fetch_with_retry(params)
            status = SnapshotStatus.SUCCESS
            error_message = None
        except Exception as exc:
            raw_payload = {"error": str(exc)}
            status = SnapshotStatus.ERROR
            error_message = str(exc)

        # 2) 스냅샷 저장 (원시 데이터 보존)
        snapshot = await create_snapshot(
            db,
            SourceSnapshotCreate(
                data_source_id=data_source_id,
                project_id=project_id,
                query_params=params,
                raw_payload=raw_payload,
                status=status,
                error_message=error_message,
            ),
        )

        # 스냅샷 ORM 객체에서 raw_payload 참조 제거 (DB에 이미 저장됨)
        # collect() 단계에서는 snapshot.id만 필요하므로 메모리 절감
        try:
            snapshot.raw_payload = None
        except Exception:
            pass

        # 3) 오류 시 빈 증거 목록 반환
        if status == SnapshotStatus.ERROR:
            return snapshot, []

        # 4) 정규화 → 증거 일괄 저장
        evidence_items = self.normalize(
            raw_payload=raw_payload,
            project_id=project_id,
            data_source_id=data_source_id,
            snapshot_id=snapshot.id,
            screening_only=screening_only,
        )

        # 원시 페이로드 메모리 해제 (스냅샷에 이미 저장됨)
        del raw_payload
        gc.collect()

        evidences: list[Evidence] = []
        if evidence_items:
            evidences = await create_evidences_bulk(db, evidence_items)

        # 정규화 결과 메모리 해제 (DB에 이미 저장됨)
        del evidence_items
        gc.collect()

        return snapshot, evidences
