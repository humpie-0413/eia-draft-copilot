"""예측 모델 추상 기반 클래스.

모든 예측 모델은 BasePredictionModel을 상속하고,
predict / get_required_inputs / get_model_info 를 구현해야 한다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelInfo:
    """모델 메타 정보."""

    name: str              # 모델 식별자 (예: "gaussian_plume")
    display_name: str      # 표시용 이름 (예: "가우시안 플룸 모델")
    description: str       # 모델 설명
    applicable_sections: list[str]  # 적용 가능한 섹션 키 목록


@dataclass
class PredictionItem:
    """개별 예측 지점/거리별 결과."""

    label: str                          # 지점 레이블 (예: "100m", "1km")
    distance_m: float                   # 풍하거리 (m)
    pollutant: str                      # 오염물질명 (예: "PM10")
    predicted_concentration: float      # 예측 농도 (ug/m3 또는 ppm)
    background_concentration: float     # 배경 농도 (현황 데이터)
    total_concentration: float          # 합산 농도 (배경 + 예측)
    unit: str                           # 단위
    standard_value: float | None = None # 환경기준값
    exceeds_standard: bool = False      # 기준 초과 여부


@dataclass
class PredictionResult:
    """예측 실행 결과."""

    section_key: str                    # 대상 섹션
    model_name: str                     # 사용 모델명
    input_parameters: dict              # 입력 파라미터 (재현 가능하도록 기록)
    predictions: list[PredictionItem] = field(default_factory=list)
    summary: str = ""                   # 요약 텍스트
    assumptions: list[str] = field(default_factory=list)  # 전제 조건
    limitations: list[str] = field(default_factory=list)  # 모델 한계


@dataclass(frozen=True)
class InputParameter:
    """모델 입력 파라미터 정의."""

    name: str           # 파라미터 이름
    display_name: str   # 표시용 이름
    unit: str           # 단위
    default: float | str | None = None  # 기본값
    required: bool = True
    description: str = ""


class BasePredictionModel(ABC):
    """예측 모델 추상 클래스.

    모든 환경영향 예측 모델은 이 클래스를 상속해야 한다.
    """

    @abstractmethod
    def predict(
        self,
        parameters: dict,
        background_data: dict[str, float] | None = None,
    ) -> PredictionResult:
        """예측을 실행한다.

        Args:
            parameters: 모델 입력 파라미터 (배출량, 굴뚝 높이 등)
            background_data: 배경 농도 데이터 (지표명 → 농도)

        Returns:
            PredictionResult: 예측 결과
        """

    @abstractmethod
    def get_required_inputs(self) -> list[InputParameter]:
        """모델에 필요한 입력 파라미터 목록을 반환한다."""

    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """모델 메타 정보를 반환한다."""
