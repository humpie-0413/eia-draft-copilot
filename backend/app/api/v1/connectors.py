"""커넥터 수집 실행 API 엔드포인트.

POST /api/v1/connectors/{connector_key}/collect
- 지정 커넥터로 외부 API를 호출하여 데이터를 수집한다.
- fetch → raw_payload 스냅샷 저장 → normalize → evidence 벌크 저장
- 데이터 소스가 DB에 없으면 자동 등록한다.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.registry import connector_registry, get_connector
from app.crud.data_source import create_data_source, get_data_source_by_key
from app.db import get_db
from app.schemas.connector import CollectRequest, CollectResult
from app.schemas.data_source import DataSourceCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("")
async def list_connectors():
    """사용 가능한 커넥터 목록을 반환한다."""
    return [
        {"connector_key": key, "display_name": conn.display_name}
        for key, conn in connector_registry.items()
    ]


@router.post(
    "/{connector_key}/collect",
    response_model=CollectResult,
    status_code=status.HTTP_200_OK,
)
async def collect_data(
    connector_key: str,
    body: CollectRequest,
    db: AsyncSession = Depends(get_db),
):
    """커넥터를 실행하여 외부 API 데이터를 수집한다.

    1. connector_key로 커넥터 인스턴스를 조회
    2. data_source가 DB에 없으면 자동 생성
    3. BaseConnector.collect() 파이프라인 실행
    4. 수집 결과 요약 반환
    """
    # 커넥터 조회
    connector = get_connector(connector_key)
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"커넥터를 찾을 수 없습니다: {connector_key}",
        )

    # 데이터 소스 조회 또는 자동 생성
    data_source = await get_data_source_by_key(db, connector_key)
    if data_source is None:
        data_source = await create_data_source(
            db,
            DataSourceCreate(
                name=connector.display_name,
                connector_key=connector_key,
                description=f"{connector.display_name} 자동 등록",
            ),
        )
        logger.info(
            "데이터 소스 자동 생성: %s (%s)",
            data_source.name,
            data_source.id,
        )

    # 수집 실행
    try:
        snapshot, evidences = await connector.collect(
            db=db,
            project_id=body.project_id,
            data_source_id=data_source.id,
            params=body.params,
            screening_only=body.screening_only,
        )
    except Exception as exc:
        logger.error("커넥터 수집 실행 실패: %s — %s", connector_key, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"외부 API 호출 실패: {exc}",
        ) from exc

    return CollectResult(
        connector_key=connector_key,
        snapshot_id=snapshot.id,
        status=snapshot.status,
        evidence_count=len(evidences),
        error_message=snapshot.error_message,
    )
