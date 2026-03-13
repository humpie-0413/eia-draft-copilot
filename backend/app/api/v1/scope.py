"""평가 범위 API 엔드포인트."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project import get_project
from app.db import get_db
from app.schemas.scope import AssessmentScopeRead, SectionScopeRead
from app.services.scope_service import get_assessment_scope

router = APIRouter(
    prefix="/projects/{project_id}/assessment-scope",
    tags=["scope"],
)


@router.get("", response_model=AssessmentScopeRead)
async def get_project_assessment_scope(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AssessmentScopeRead:
    """프로젝트의 사업유형 기반 평가 범위를 반환한다.

    사업유형이 미설정이면 'other' 기준으로 평가 범위를 산정한다.
    """
    project = await get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="프로젝트를 찾을 수 없습니다.")

    project_type = project.project_type or "other"
    scope = get_assessment_scope(project_type)

    return AssessmentScopeRead(
        project_type=scope.project_type,
        type_name=scope.type_name,
        legal_basis=scope.legal_basis,
        sections=[
            SectionScopeRead(
                section_key=s.section_key,
                title=s.title,
                scope=s.scope,
                required_indicators=s.required_indicators,
                legal_basis=s.legal_basis,
            )
            for s in scope.sections
        ],
        required_count=scope.required_count,
        recommended_count=scope.recommended_count,
        optional_count=scope.optional_count,
    )
