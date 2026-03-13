"""예측 모델 레지스트리.

section_key → 사용 가능한 모델 매핑을 관리한다.
새 예측 모델 추가 시 이 파일에 등록하면 자동으로 API에 노출된다.
"""

from __future__ import annotations

from app.services.prediction.air_dispersion import AirDispersionModel
from app.services.prediction.base import BasePredictionModel, ModelInfo


# 모델 인스턴스 레지스트리 (모델명 → 인스턴스)
_MODEL_REGISTRY: dict[str, BasePredictionModel] = {
    "gaussian_plume": AirDispersionModel(),
}

# 섹션 키 → 사용 가능한 모델명 목록
_SECTION_MODELS: dict[str, list[str]] = {
    "air_quality": ["gaussian_plume"],
}


def get_model(model_name: str) -> BasePredictionModel | None:
    """모델명으로 모델 인스턴스를 반환한다."""
    return _MODEL_REGISTRY.get(model_name)


def get_models_for_section(section_key: str) -> list[BasePredictionModel]:
    """섹션에 사용 가능한 모델 인스턴스 목록을 반환한다."""
    model_names = _SECTION_MODELS.get(section_key, [])
    return [_MODEL_REGISTRY[name] for name in model_names if name in _MODEL_REGISTRY]


def list_models() -> list[ModelInfo]:
    """등록된 모든 모델의 메타 정보를 반환한다."""
    return [model.get_model_info() for model in _MODEL_REGISTRY.values()]


def get_default_model_for_section(section_key: str) -> BasePredictionModel | None:
    """섹션의 기본 모델을 반환한다 (첫 번째 등록 모델)."""
    models = get_models_for_section(section_key)
    return models[0] if models else None
