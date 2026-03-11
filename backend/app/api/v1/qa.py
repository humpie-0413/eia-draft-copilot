"""QA 규칙 엔진 API 엔드포인트."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project import get_project
from app.db import get_db
from app.schemas.qa import ExportReadyRead, QaIssueRead, QaResultRead, QaSummaryRead
from app.services.qa_engine import QaResult, run_qa

router = APIRouter(
    prefix="/projects/{project_id}/qa",
    tags=["qa"],
)


async def _verify_project(
    db: AsyncSession, project_id: uuid.UUID
) -> None:
    """프로젝트 존재 여부 확인."""
    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")


def _qa_result_to_read(result: QaResult) -> QaResultRead:
    """QaResult 데이터클래스를 Pydantic 응답 모델로 변환."""
    return QaResultRead(
        project_id=result.project_id,
        run_at=result.run_at,
        issues=[
            QaIssueRead(
                rule_id=issue.rule_id,
                severity=issue.severity.value,
                section_key=issue.section_key,
                title=issue.title,
                message=issue.message,
                indicators=issue.indicators,
            )
            for issue in result.issues
        ],
        summary=QaSummaryRead(
            critical_count=result.summary.critical_count,
            warning_count=result.summary.warning_count,
            info_count=result.summary.info_count,
            total=result.summary.total,
        ),
        export_ready=result.export_ready,
    )


@router.get("", response_model=QaResultRead)
async def get_qa_result(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> QaResultRead:
    """프로젝트에 대해 QA 규칙 엔진을 실행하고 결과를 반환한다."""
    await _verify_project(db, project_id)
    result = await run_qa(db, project_id)
    return _qa_result_to_read(result)


@router.get("/export-ready", response_model=ExportReadyRead)
async def check_export_ready(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ExportReadyRead:
    """export 가능 여부만 간략히 확인한다."""
    await _verify_project(db, project_id)
    result = await run_qa(db, project_id)

    if result.export_ready:
        message = "모든 critical 이슈가 해결되었습니다. Export가 가능합니다."
    else:
        message = (
            f"critical 이슈 {result.summary.critical_count}건이 "
            f"남아 있습니다. 해결 후 export할 수 있습니다."
        )

    return ExportReadyRead(
        project_id=result.project_id,
        export_ready=result.export_ready,
        critical_count=result.summary.critical_count,
        message=message,
    )
