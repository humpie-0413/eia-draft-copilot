"""예측 모듈 API 응답 Pydantic 스키마."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PredictionItemRead(BaseModel):
    """개별 예측 지점 결과."""

    label: str = Field(..., description="지점 레이블 (예: 100m, 1km)")
    distance_m: float = Field(..., description="풍하거리 (m)")
    pollutant: str = Field(..., description="오염물질명")
    predicted_concentration: float = Field(..., description="예측 기여 농도")
    background_concentration: float = Field(..., description="배경 농도")
    total_concentration: float = Field(..., description="합산 농도")
    unit: str = Field(..., description="농도 단위")
    standard_value: float | None = Field(None, description="환경기준값")
    exceeds_standard: bool = Field(False, description="기준 초과 여부")


class PredictionResultRead(BaseModel):
    """예측 실행 결과."""

    section_key: str = Field(..., description="대상 섹션")
    model_name: str = Field(..., description="사용 모델명")
    input_parameters: dict = Field(default_factory=dict, description="입력 파라미터")
    predictions: list[PredictionItemRead] = Field(
        default_factory=list, description="예측 결과 목록"
    )
    summary: str = Field("", description="요약 텍스트")
    assumptions: list[str] = Field(default_factory=list, description="전제 조건")
    limitations: list[str] = Field(default_factory=list, description="모델 한계")


class InputParameterRead(BaseModel):
    """모델 입력 파라미터 정의."""

    name: str = Field(..., description="파라미터 이름")
    display_name: str = Field(..., description="표시용 이름")
    unit: str = Field(..., description="단위")
    default: float | str | None = Field(None, description="기본값")
    required: bool = Field(True, description="필수 여부")
    description: str = Field("", description="설명")


class ModelInfoRead(BaseModel):
    """예측 모델 메타 정보."""

    name: str = Field(..., description="모델 식별자")
    display_name: str = Field(..., description="표시용 이름")
    description: str = Field(..., description="모델 설명")
    applicable_sections: list[str] = Field(
        default_factory=list, description="적용 가능한 섹션"
    )
    required_inputs: list[InputParameterRead] = Field(
        default_factory=list, description="필요 입력 파라미터"
    )


class PredictionRequest(BaseModel):
    """예측 실행 요청."""

    model_name: str | None = Field(
        None,
        description="모델명 (미지정 시 섹션 기본 모델 사용)",
    )
    parameters: dict = Field(
        default_factory=dict,
        description="모델 입력 파라미터",
    )
    use_background_data: bool = Field(
        True,
        description="기존 대기질 현황 데이터를 배경 농도로 사용할지 여부",
    )
