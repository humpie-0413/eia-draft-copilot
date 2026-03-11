"""공공데이터 커넥터 기본 인터페이스.

모든 커넥터는 BaseConnector를 상속하며, fetch()와 normalize()를 구현해야 한다.
fetch()는 외부 API를 호출하여 원시 응답을 반환하고,
normalize()는 원시 응답을 EvidenceCreate 목록으로 변환한다.
"""

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
        # 1) 외부 API 호출
        try:
            raw_payload = await self.fetch(params)
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

        evidences = []
        if evidence_items:
            evidences = await create_evidences_bulk(db, evidence_items)

        return snapshot, evidences
