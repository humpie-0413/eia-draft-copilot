"""DOCX/PDF 출력 API 엔드포인트.

Post-5 개편: Export 옵션(부록 포함 여부), 미리보기 엔드포인트 추가.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project import get_project
from app.db import get_db
from app.services.export_service import (
    ExportOptions,
    ExportPreview,
    generate_docx,
    generate_export_preview,
    generate_pdf,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/export",
    tags=["export"],
)


# ── 응답 스키마 ──

class PreviewSectionResponse(BaseModel):
    """미리보기 섹션 정보."""

    title: str
    state: str
    evidence_count: int
    has_stats: bool
    has_standards: bool


class ExportPreviewResponse(BaseModel):
    """Export 미리보기 응답."""

    project_name: str
    project_type: str | None
    centroid: list[float] | None  # [위도, 경도]
    sections: list[PreviewSectionResponse]
    total_evidence: int
    similar_case_count: int
    qa_issue_count: int
    export_ready: bool


# ── 엔드포인트 ──

@router.get("/preview")
async def export_preview(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ExportPreviewResponse:
    """Export 전 문서 구조 미리보기를 반환한다.

    표지, 목차, 각 섹션의 상태 및 증거 건수, 부록 데이터 현황을 보여준다.
    """
    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    try:
        preview = await generate_export_preview(db, project)
    except Exception as e:
        logger.exception("미리보기 생성 중 예외 발생")
        raise HTTPException(status_code=500, detail=str(e))

    return ExportPreviewResponse(
        project_name=preview.project_name,
        project_type=preview.project_type,
        centroid=list(preview.centroid) if preview.centroid else None,
        sections=[
            PreviewSectionResponse(
                title=s.title,
                state=s.state,
                evidence_count=s.evidence_count,
                has_stats=s.has_stats,
                has_standards=s.has_standards,
            )
            for s in preview.sections
        ],
        total_evidence=preview.total_evidence,
        similar_case_count=preview.similar_case_count,
        qa_issue_count=preview.qa_issue_count,
        export_ready=preview.export_ready,
    )


@router.post("/docx")
async def export_docx(
    project_id: uuid.UUID,
    include_appendix_a: bool = Query(True, description="부록 A: 상세 측정 데이터 포함"),
    include_appendix_b: bool = Query(True, description="부록 B: 유사사례 매칭 결과 포함"),
    include_appendix_c: bool = Query(True, description="부록 C: QA 검사 결과 포함"),
    skip_qa_check: bool = Query(False, description="QA 검사 건너뛰기 (데모/테스트용)"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """초안 뼈대를 DOCX 문서로 출력한다.

    critical QA 이슈가 있으면 export가 차단된다(Export Gate).
    skip_qa_check=true 시 QA 검사를 건너뛴다.
    """
    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    options = ExportOptions(
        include_appendix_a=include_appendix_a,
        include_appendix_b=include_appendix_b,
        include_appendix_c=include_appendix_c,
    )

    try:
        buffer, filename = await generate_docx(
            db, project, options=options, skip_qa_check=skip_qa_check
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("DOCX 생성 중 예외 발생")
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(
        buffer,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.get("/pdf")
async def export_pdf(
    project_id: uuid.UUID,
    include_appendix_a: bool = Query(True, description="부록 A: 상세 측정 데이터 포함"),
    include_appendix_b: bool = Query(True, description="부록 B: 유사사례 매칭 결과 포함"),
    include_appendix_c: bool = Query(True, description="부록 C: QA 검사 결과 포함"),
    skip_qa_check: bool = Query(False, description="QA 검사 건너뛰기 (데모/테스트용)"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """초안 뼈대를 PDF 문서로 출력한다.

    critical QA 이슈가 있으면 export가 차단된다(Export Gate).
    skip_qa_check=true 시 QA 검사를 건너뛴다.
    """
    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    options = ExportOptions(
        include_appendix_a=include_appendix_a,
        include_appendix_b=include_appendix_b,
        include_appendix_c=include_appendix_c,
    )

    try:
        buffer, filename = await generate_pdf(
            db, project, options=options, skip_qa_check=skip_qa_check
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("PDF 생성 중 예외 발생")
        raise HTTPException(status_code=500, detail=str(e))

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
