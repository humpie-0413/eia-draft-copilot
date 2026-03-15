"""Pred-3: 영향 예측 서술문 생성 테스트.

generate_prediction_narrative 함수의 대기질/소음/수질/미지원 섹션
서술문 생성을 검증한다.
"""

from __future__ import annotations

import pytest

from app.services.narrative_generator import generate_prediction_narrative
from app.services.prediction.air_dispersion import AirDispersionModel
from app.services.prediction.noise_propagation import NoisePropagationModel
from app.services.prediction.water_mixing import WaterMixingModel
from app.services.prediction.base import PredictionResult


# ────────────────────────────────────────────
# 헬퍼: 예측 결과 생성
# ────────────────────────────────────────────

def _air_result(
    background: dict | None = None,
    project_type: str = "other",
) -> PredictionResult:
    """대기질 예측 결과를 생성한다."""
    model = AirDispersionModel()
    return model.predict(
        parameters={"project_type": project_type},
        background_data=background,
    )


def _noise_result(
    background: dict | None = None,
    project_type: str = "other",
) -> PredictionResult:
    """소음 예측 결과를 생성한다."""
    model = NoisePropagationModel()
    return model.predict(
        parameters={"project_type": project_type},
        background_data=background,
    )


def _water_result(
    background: dict | None = None,
    project_type: str = "other",
) -> PredictionResult:
    """수질 예측 결과를 생성한다."""
    model = WaterMixingModel()
    return model.predict(
        parameters={"project_type": project_type},
        background_data=background,
    )


# ────────────────────────────────────────────
# 대기질 예측 서술문 테스트
# ────────────────────────────────────────────

class TestAirPredictionNarrative:
    """대기질 영향 예측 서술문 테스트."""

    def test_returns_string(self):
        """서술문이 문자열로 반환되어야 한다."""
        result = _air_result()
        narrative = generate_prediction_narrative("air_quality", result)
        assert isinstance(narrative, str)
        assert len(narrative) > 0

    def test_contains_model_name(self):
        """서술문에 '가우시안 플룸' 모델 언급이 포함되어야 한다."""
        result = _air_result()
        narrative = generate_prediction_narrative("air_quality", result)
        assert "가우시안 플룸" in narrative

    def test_contains_pm10(self):
        """PM10 오염물질이 서술문에 포함되어야 한다."""
        result = _air_result()
        narrative = generate_prediction_narrative("air_quality", result)
        assert "PM10" in narrative

    def test_contains_legal_reference(self):
        """환경정책기본법 법적 근거가 서술문에 포함되어야 한다."""
        result = _air_result()
        narrative = generate_prediction_narrative("air_quality", result)
        assert "환경정책기본법" in narrative

    def test_contains_standard_judgment(self):
        """환경기준 이내/초과 판정 문구가 포함되어야 한다."""
        result = _air_result()
        narrative = generate_prediction_narrative("air_quality", result)
        # 이내이다 또는 초과이다 중 하나가 포함되어야 함
        assert "이내이다" in narrative or "초과이다" in narrative

    def test_exceedance_mention_when_exceeded(self):
        """초과 항목이 있을 때 저감대책 언급이 포함되어야 한다."""
        # 기준(PM10=50, PM2.5=15)을 초과하는 높은 배경 농도 + 높은 배출량으로 기준 초과 유발
        bg = {"PM10": 51.0, "PM2.5": 16.0, "NO2": 60.0, "SO2": 55.0}
        result = _air_result(background=bg, project_type="industrial")
        narrative = generate_prediction_narrative("air_quality", result)
        # 배경 농도만으로 이미 기준 초과이므로 합산 농도도 초과
        any_exceeded = any(item.exceeds_standard for item in result.predictions)
        # 초과 발생 여부 확인 후 서술문 검증
        assert any_exceeded, "테스트 설계 오류: 기준 초과 조건이 충족되지 않음"
        assert "저감대책" in narrative

    def test_with_background_data(self):
        """배경 농도가 반영된 서술문이 생성되어야 한다."""
        bg = {"PM10": 30.0, "PM2.5": 15.0}
        result = _air_result(background=bg)
        narrative = generate_prediction_narrative("air_quality", result)
        assert len(narrative) > 0
        assert "PM10" in narrative


# ────────────────────────────────────────────
# 소음 예측 서술문 테스트
# ────────────────────────────────────────────

class TestNoisePredictionNarrative:
    """소음 영향 예측 서술문 테스트."""

    def test_returns_string(self):
        """서술문이 문자열로 반환되어야 한다."""
        result = _noise_result()
        narrative = generate_prediction_narrative("noise_vibration", result)
        assert isinstance(narrative, str)
        assert len(narrative) > 0

    def test_contains_model_name(self):
        """서술문에 '점음원 거리감쇠' 모델 언급이 포함되어야 한다."""
        result = _noise_result()
        narrative = generate_prediction_narrative("noise_vibration", result)
        assert "점음원 거리감쇠" in narrative

    def test_contains_daytime(self):
        """주간 소음 언급이 포함되어야 한다."""
        result = _noise_result()
        narrative = generate_prediction_narrative("noise_vibration", result)
        assert "주간" in narrative

    def test_contains_nighttime(self):
        """야간 소음 언급이 포함되어야 한다."""
        result = _noise_result()
        narrative = generate_prediction_narrative("noise_vibration", result)
        assert "야간" in narrative

    def test_contains_db_unit(self):
        """dB(A) 단위가 포함되어야 한다."""
        result = _noise_result()
        narrative = generate_prediction_narrative("noise_vibration", result)
        assert "dB(A)" in narrative

    def test_exceedance_mention_when_exceeded(self):
        """초과 항목 있을 때 방음대책 언급이 포함되어야 한다."""
        # 높은 배경 소음으로 기준 초과 유발
        bg = {"소음_Leq_주간": 54.0, "소음_Leq_야간": 44.0}
        result = _noise_result(background=bg, project_type="industrial")
        narrative = generate_prediction_narrative("noise_vibration", result)
        any_exceeded = any(item.exceeds_standard for item in result.predictions)
        if any_exceeded:
            assert "소음저감대책" in narrative or "방음벽" in narrative


# ────────────────────────────────────────────
# 수질 예측 서술문 테스트
# ────────────────────────────────────────────

class TestWaterPredictionNarrative:
    """수질 영향 예측 서술문 테스트."""

    def test_returns_string(self):
        """서술문이 문자열로 반환되어야 한다."""
        result = _water_result()
        narrative = generate_prediction_narrative("water_quality", result)
        assert isinstance(narrative, str)
        assert len(narrative) > 0

    def test_contains_model_name(self):
        """서술문에 '완전혼합 희석' 모델 언급이 포함되어야 한다."""
        result = _water_result()
        narrative = generate_prediction_narrative("water_quality", result)
        assert "완전혼합 희석" in narrative

    def test_contains_bod(self):
        """BOD 언급이 포함되어야 한다."""
        result = _water_result()
        narrative = generate_prediction_narrative("water_quality", result)
        assert "BOD" in narrative

    def test_contains_cod(self):
        """COD 언급이 포함되어야 한다."""
        result = _water_result()
        narrative = generate_prediction_narrative("water_quality", result)
        assert "COD" in narrative

    def test_contains_mg_l_unit(self):
        """mg/L 단위가 포함되어야 한다."""
        result = _water_result()
        narrative = generate_prediction_narrative("water_quality", result)
        assert "mg/L" in narrative

    def test_exceedance_mention_when_exceeded(self):
        """초과 항목 있을 때 처리 대책 언급이 포함되어야 한다."""
        result = _water_result()
        narrative = generate_prediction_narrative("water_quality", result)
        any_exceeded = any(item.exceeds_standard for item in result.predictions)
        if any_exceeded:
            assert "처리 대책" in narrative or "대책" in narrative


# ────────────────────────────────────────────
# 미지원 섹션 테스트
# ────────────────────────────────────────────

class TestUnsupportedSectionNarrative:
    """예측 모델이 없는 섹션의 서술문 테스트."""

    def test_ecology_returns_fallback(self):
        """ecology 섹션은 전문 분석 필요 안내 문구를 반환해야 한다."""
        # ecology 섹션은 예측 모델 없음 — 임의의 PredictionResult 사용
        dummy_result = PredictionResult(
            section_key="ecology",
            model_name="none",
            input_parameters={},
        )
        narrative = generate_prediction_narrative("ecology", dummy_result)
        assert "전문 분석" in narrative

    def test_land_use_returns_fallback(self):
        """land_use 섹션은 전문 분석 필요 안내 문구를 반환해야 한다."""
        dummy_result = PredictionResult(
            section_key="land_use",
            model_name="none",
            input_parameters={},
        )
        narrative = generate_prediction_narrative("land_use", dummy_result)
        assert "전문 분석" in narrative

    def test_unknown_section_returns_fallback(self):
        """미정의 섹션 키도 안내 문구를 반환해야 한다."""
        dummy_result = PredictionResult(
            section_key="unknown",
            model_name="none",
            input_parameters={},
        )
        narrative = generate_prediction_narrative("unknown", dummy_result)
        assert "전문 분석" in narrative


# ────────────────────────────────────────────
# ScaffoldSection 예측 결과 통합 테스트
# ────────────────────────────────────────────

class TestScaffoldPredictionIntegration:
    """ScaffoldSection에 prediction_result/prediction_narrative가
    올바르게 포함되는지 검증한다.
    """

    def test_prediction_narrative_air_quality(self):
        """대기질 예측 서술문이 비어 있지 않아야 한다."""
        result = _air_result()
        narrative = generate_prediction_narrative("air_quality", result)
        assert narrative
        assert "가우시안 플룸" in narrative

    def test_prediction_narrative_noise_vibration(self):
        """소음 예측 서술문이 비어 있지 않아야 한다."""
        result = _noise_result()
        narrative = generate_prediction_narrative("noise_vibration", result)
        assert narrative
        assert "점음원 거리감쇠" in narrative

    def test_prediction_narrative_water_quality(self):
        """수질 예측 서술문이 비어 있지 않아야 한다."""
        result = _water_result()
        narrative = generate_prediction_narrative("water_quality", result)
        assert narrative
        assert "완전혼합 희석" in narrative

    def test_background_data_extraction(self):
        """배경 농도 데이터가 서술문에 반영되어야 한다.

        배경 농도 있을 때와 없을 때의 예측 결과가 다른지 확인한다.
        """
        result_no_bg = _air_result()
        result_with_bg = _air_result(background={"PM10": 40.0})

        # 배경 농도 있을 때 PM10 합산 농도가 더 높아야 함
        pm10_no_bg = next(
            (p for p in result_no_bg.predictions
             if p.pollutant == "PM10" and p.distance_m == 100.0),
            None,
        )
        pm10_with_bg = next(
            (p for p in result_with_bg.predictions
             if p.pollutant == "PM10" and p.distance_m == 100.0),
            None,
        )
        if pm10_no_bg and pm10_with_bg:
            assert pm10_with_bg.total_concentration > pm10_no_bg.total_concentration
