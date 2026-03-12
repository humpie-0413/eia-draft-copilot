"""DOCX/PDF 출력 API 엔드포인트."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project import get_project
from app.db import get_db
from app.services.export_service import generate_docx, generate_pdf

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/projects/{project_id}/export",
    tags=["export"],
)


@router.post("/docx")
async def export_docx(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """초안 뼈대를 DOCX 문서로 출력한다.

    critical QA 이슈가 있으면 export가 차단된다(Export Gate).
    """
    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    try:
        buffer, filename = await generate_docx(
            db, project_id, project.name
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
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """초안 뼈대를 PDF 문서로 출력한다.

    critical QA 이슈가 있으면 export가 차단된다(Export Gate).
    """
    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    try:
        buffer, filename = await generate_pdf(
            db, project_id, project.name
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
