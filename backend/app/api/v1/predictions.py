"""예측 모듈 API 엔드포인트.

환경영향 예측 모델 실행 및 결과 조회를 제공한다.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import project as project_crud
from app.db import get_db
from app.models.evidence import Evidence
from app.schemas.prediction import (
    InputParameterRead,
    ModelInfoRead,
    PredictionItemRead,
    PredictionRequest,
    PredictionResultRead,
)
from app.services.prediction.registry import (
    get_default_model_for_section,
    get_model,
    list_models,
)

router = APIRouter(tags=["predictions"])


# ────────────────────────────────────────────
# 헬퍼
# ────────────────────────────────────────────

async def _verify_project(db: AsyncSession, project_id: uuid.UUID):
    """프로젝트 존재 여부를 확인한다."""
    project = await project_crud.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"프로젝트를 찾을 수 없습니다: {project_id}",
        )
    return project


async def _get_background_air_data(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict[str, float]:
    """프로젝트의 대기질 현황 데이터에서 배경 농도를 추출한다.

    에어코리아 수집 데이터의 연평균 지표를 배경 농도로 사용한다.
    """
    # 연평균 지표 매핑 (evidence indicator → 모델 오염물질명)
    indicator_map = {
        "PM10_연평균": "PM10",
        "PM2.5_연평균": "PM2.5",
        "NO2_연평균": "NO2",
        "SO2_연평균": "SO2",
    }

    result = await db.execute(
        select(Evidence).where(
            and_(
                Evidence.project_id == project_id,
                Evidence.category == "air_quality",
                Evidence.screening_only.is_(False),
                Evidence.numeric_value.isnot(None),
                Evidence.indicator.in_(list(indicator_map.keys())),
            )
        )
    )
    evidences = result.scalars().all()

    # 지표별 평균 계산
    values_by_pollutant: dict[str, list[float]] = {}
    for ev in evidences:
        pollutant = indicator_map.get(ev.indicator)
        if pollutant and ev.numeric_value is not None:
            values_by_pollutant.setdefault(pollutant, []).append(ev.numeric_value)

    background: dict[str, float] = {}
    for pollutant, values in values_by_pollutant.items():
        if values:
            background[pollutant] = sum(values) / len(values)

    return background


async def _get_wind_speed_from_evidence(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> float | None:
    """프로젝트의 기후 데이터에서 평균 풍속을 추출한다."""
    result = await db.execute(
        select(Evidence).where(
            and_(
                Evidence.project_id == project_id,
                Evidence.category == "climate",
                Evidence.indicator == "평균풍속",
                Evidence.screening_only.is_(False),
                Evidence.numeric_value.isnot(None),
            )
        )
    )
    evidences = result.scalars().all()

    if not evidences:
        return None

    values = [ev.numeric_value for ev in evidences if ev.numeric_value is not None]
    if not values:
        return None

    return sum(values) / len(values)


def _result_to_read(result) -> PredictionResultRead:
    """PredictionResult 데이터클래스를 Pydantic 모델로 변환."""
    return PredictionResultRead(
        section_key=result.section_key,
        model_name=result.model_name,
        input_parameters=result.input_parameters,
        predictions=[
            PredictionItemRead(
                label=p.label,
                distance_m=p.distance_m,
                pollutant=p.pollutant,
                predicted_concentration=p.predicted_concentration,
                background_concentration=p.background_concentration,
                total_concentration=p.total_concentration,
                unit=p.unit,
                standard_value=p.standard_value,
                exceeds_standard=p.exceeds_standard,
            )
            for p in result.predictions
        ],
        summary=result.summary,
        assumptions=result.assumptions,
        limitations=result.limitations,
    )


# ────────────────────────────────────────────
# 엔드포인트
# ────────────────────────────────────────────

@router.post(
    "/projects/{project_id}/predict/{section_key}",
    response_model=PredictionResultRead,
    summary="예측 실행",
)
async def run_prediction(
    project_id: uuid.UUID,
    section_key: str,
    body: PredictionRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """지정 섹션에 대한 환경영향 예측을 실행한다.

    파라미터를 직접 입력하거나, 사업유형별 기본값을 사용할 수 있다.
    use_background_data=True 이면 기존 대기질 현황 데이터를 배경 농도로 사용한다.
    """
    project = await _verify_project(db, project_id)
    req = body or PredictionRequest()

    # 모델 선택
    if req.model_name:
        model = get_model(req.model_name)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"사용 가능한 모델이 아닙니다: {req.model_name}",
            )
    else:
        model = get_default_model_for_section(section_key)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"해당 섹션에 사용 가능한 예측 모델이 없습니다: {section_key}",
            )

    # 파라미터 준비
    params = dict(req.parameters)

    # 사업유형 자동 설정
    if "project_type" not in params and project.project_type:
        params["project_type"] = project.project_type

    # 풍속 자동 추출 (파라미터에 미지정 시)
    if "wind_speed" not in params:
        ws = await _get_wind_speed_from_evidence(db, project_id)
        if ws is not None:
            params["wind_speed"] = ws

    # 배경 농도 데이터
    background: dict[str, float] | None = None
    if req.use_background_data and section_key == "air_quality":
        background = await _get_background_air_data(db, project_id)

    # 예측 실행
    result = model.predict(parameters=params, background_data=background)

    return _result_to_read(result)


@router.get(
    "/prediction-models",
    response_model=list[ModelInfoRead],
    summary="사용 가능한 예측 모델 목록",
)
async def get_prediction_models():
    """등록된 모든 예측 모델의 메타 정보를 반환한다."""
    models = list_models()
    result = []
    for info in models:
        # 해당 모델의 입력 파라미터도 포함
        model_instance = get_model(info.name)
        inputs = []
        if model_instance:
            inputs = [
                InputParameterRead(
                    name=inp.name,
                    display_name=inp.display_name,
                    unit=inp.unit,
                    default=inp.default,
                    required=inp.required,
                    description=inp.description,
                )
                for inp in model_instance.get_required_inputs()
            ]
        result.append(ModelInfoRead(
            name=info.name,
            display_name=info.display_name,
            description=info.description,
            applicable_sections=info.applicable_sections,
            required_inputs=inputs,
        ))
    return result
