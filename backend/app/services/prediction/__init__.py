"""예측 모듈 패키지.

환경영향 예측 모델을 통합 관리한다.
현재 지원 모델: 대기 확산 (가우시안 플룸)
"""

from app.services.prediction.base import (
    BasePredictionModel,
    ModelInfo,
    PredictionItem,
    PredictionResult,
)
from app.services.prediction.registry import get_model, list_models

__all__ = [
    "BasePredictionModel",
    "ModelInfo",
    "PredictionItem",
    "PredictionResult",
    "get_model",
    "list_models",
]
