"""소음 전파 모델 및 수질 혼합 모델 테스트.

소음 감쇠 계산 정확성, 에너지 합산, 차음벽 효과,
수질 혼합 계산 정확성, API 엔드포인트를 검증한다.
"""

from __future__ import annotations

import math
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.prediction.noise_propagation import (
    ATMOSPHERIC_ABSORPTION_COEFF,
    DEFAULT_SOURCE_PARAMS,
    NOISE_STANDARDS,
    PREDICTION_DISTANCES as NOISE_DISTANCES,
    NoisePropagationModel,
    energy_sum_db,
    line_source_attenuation,
    maekawa_barrier_attenuation,
    point_source_attenuation,
)
from app.services.prediction.water_mixing import (
    DEFAULT_DISCHARGE_FLOW,
    DEFAULT_RIVER_FLOW,
    DISCHARGE_STANDARDS,
    POLLUTANT_INFO as WATER_POLLUTANT_INFO,
    TARGET_POLLUTANTS as WATER_TARGET_POLLUTANTS,
    WaterMixingModel,
    complete_mixing_concentration,
)
from app.services.prediction.registry import (
    get_default_model_for_section,
    get_model,
    get_models_for_section,
    list_models,
)


# ════════════════════════════════════════════
# 1. 소음 전파 모델 — 점음원 감쇠 테스트
# ════════════════════════════════════════════

class TestPointSourceAttenuation:
    """점음원 거리감쇠 계산 테스트."""

    def test_zero_distance(self):
        """거리 0이면 결과 0이어야 한다."""
        assert point_source_attenuation(95, 0) == 0.0

    def test_negative_distance(self):
        """음수 거리이면 결과 0이어야 한다."""
        assert point_source_attenuation(95, -10) == 0.0

    def test_zero_power_level(self):
        """음향파워레벨 0이면 결과 0이어야 한다."""
        assert point_source_attenuation(0, 100) == 0.0

    def test_known_distance_100m(self):
        """100m에서 수동 계산과 일치하는지 검증.

        Lw=95, r=100m
        L = 95 - 20·log10(100) - 11 + 3 - 0.005·100
        = 95 - 40 - 11 + 3 - 0.5 = 46.5 dB
        """
        expected = 95.0 - 20.0 * math.log10(100) - 11.0 + 3.0 - 0.005 * 100
        actual = point_source_attenuation(95, 100)
        assert abs(actual - expected) < 0.01

    def test_known_distance_10m(self):
        """10m에서 수동 계산 검증.

        L = 95 - 20·log10(10) - 11 + 3 - 0.005·10
        = 95 - 20 - 11 + 3 - 0.05 = 66.95 dB
        """
        expected = 95.0 - 20.0 * math.log10(10) - 11.0 + 3.0 - 0.005 * 10
        actual = point_source_attenuation(95, 10)
        assert abs(actual - expected) < 0.01

    def test_attenuation_increases_with_distance(self):
        """거리가 멀수록 소음도가 낮아져야 한다."""
        L10 = point_source_attenuation(95, 10)
        L50 = point_source_attenuation(95, 50)
        L200 = point_source_attenuation(95, 200)
        assert L10 > L50 > L200

    def test_doubling_distance_minus_6db(self):
        """점음원: 거리 2배 시 약 6dB 감소 (대기흡수 무시 시).

        20·log10(2) ≈ 6.02 dB
        """
        L1 = point_source_attenuation(95, 50, atmospheric_absorption=False)
        L2 = point_source_attenuation(95, 100, atmospheric_absorption=False)
        diff = L1 - L2
        assert abs(diff - 6.02) < 0.1

    def test_no_ground_reflection(self):
        """지면 반사 미적용 시 3dB 낮아야 한다."""
        with_reflection = point_source_attenuation(95, 100)
        without_reflection = point_source_attenuation(
            95, 100, ground_reflection=False
        )
        assert abs(with_reflection - without_reflection - 3.0) < 0.01

    def test_atmospheric_absorption_effect(self):
        """대기 흡수 적용 시 미적용보다 낮아야 한다."""
        with_absorption = point_source_attenuation(95, 500)
        without_absorption = point_source_attenuation(
            95, 500, atmospheric_absorption=False
        )
        assert with_absorption < without_absorption


# ════════════════════════════════════════════
# 2. 소음 전파 모델 — 선음원 감쇠 테스트
# ════════════════════════════════════════════

class TestLineSourceAttenuation:
    """선음원(도로) 거리감쇠 계산 테스트."""

    def test_zero_distance(self):
        """거리 0이면 결과 0이어야 한다."""
        assert line_source_attenuation(75, 0) == 0.0

    def test_known_distance_50m(self):
        """50m에서 수동 계산 검증.

        L = 75 - 10·log10(50) - 8 + 3 - 0.005·50
        = 75 - 16.99 - 8 + 3 - 0.25 = 52.76 dB
        """
        expected = 75.0 - 10.0 * math.log10(50) - 8.0 + 3.0 - 0.005 * 50
        actual = line_source_attenuation(75, 50)
        assert abs(actual - expected) < 0.01

    def test_doubling_distance_minus_3db(self):
        """선음원: 거리 2배 시 약 3dB 감소 (대기흡수 무시 시).

        10·log10(2) ≈ 3.01 dB
        """
        L1 = line_source_attenuation(75, 50, atmospheric_absorption=False)
        L2 = line_source_attenuation(75, 100, atmospheric_absorption=False)
        diff = L1 - L2
        assert abs(diff - 3.01) < 0.1

    def test_attenuation_increases_with_distance(self):
        """거리가 멀수록 소음도가 낮아져야 한다."""
        L10 = line_source_attenuation(75, 10)
        L100 = line_source_attenuation(75, 100)
        L500 = line_source_attenuation(75, 500)
        assert L10 > L100 > L500


# ════════════════════════════════════════════
# 3. 차음벽 감쇠 테스트
# ════════════════════════════════════════════

class TestBarrierAttenuation:
    """Maekawa 차음벽 회절 감쇠 테스트."""

    def test_no_barrier(self):
        """차음벽 높이 0이면 감쇠 0이어야 한다."""
        assert maekawa_barrier_attenuation(0, 1.0, 1.2, 100) == 0.0

    def test_zero_distance(self):
        """거리 0이면 감쇠 0이어야 한다."""
        assert maekawa_barrier_attenuation(3.0, 1.0, 1.2, 0) == 0.0

    def test_positive_attenuation(self):
        """유효한 차음벽은 양수 감쇠를 제공해야 한다."""
        atten = maekawa_barrier_attenuation(5.0, 1.0, 1.2, 100)
        assert atten > 0

    def test_higher_barrier_more_attenuation(self):
        """높은 차음벽이 더 큰 감쇠를 제공해야 한다."""
        atten_3m = maekawa_barrier_attenuation(3.0, 1.0, 1.2, 100)
        atten_5m = maekawa_barrier_attenuation(5.0, 1.0, 1.2, 100)
        assert atten_5m > atten_3m

    def test_max_attenuation_limit(self):
        """최대 감쇠량은 25dB를 넘지 않아야 한다."""
        atten = maekawa_barrier_attenuation(20.0, 1.0, 1.2, 50)
        assert atten <= 25.0

    def test_barrier_below_line_of_sight(self):
        """차음벽이 직선 경로보다 낮으면 감쇠 0이어야 한다."""
        # 음원 높이 5m, 수음점 5m → 중간 높이 5m
        # 차음벽 3m < 5m → 효과 없음
        atten = maekawa_barrier_attenuation(3.0, 5.0, 5.0, 100)
        assert atten == 0.0

    def test_typical_3m_barrier(self):
        """일반적인 3m 차음벽의 감쇠량이 합리적 범위인지 확인.

        음원 1m, 수음점 1.2m, 100m 거리
        → 직선 높이 ~1.1m, 유효 높이 ~1.9m → 5~15dB 범위 예상
        """
        atten = maekawa_barrier_attenuation(3.0, 1.0, 1.2, 100)
        assert 5.0 <= atten <= 20.0


# ════════════════════════════════════════════
# 4. 에너지 합산 테스트
# ════════════════════════════════════════════

class TestEnergySum:
    """에너지 합산 계산 테스트."""

    def test_same_level_plus_3db(self):
        """같은 레벨 두 개 합산 시 +3dB.

        10·log10(10^(60/10) + 10^(60/10)) = 10·log10(2·10^6) ≈ 63.01
        """
        result = energy_sum_db(60.0, 60.0)
        assert abs(result - 63.01) < 0.1

    def test_10db_difference(self):
        """10dB 차이 시 큰 값에 +0.41dB.

        10·log10(10^(70/10) + 10^(60/10)) ≈ 70.41
        """
        result = energy_sum_db(70.0, 60.0)
        assert abs(result - 70.41) < 0.1

    def test_zero_plus_value(self):
        """0 + L = L."""
        assert energy_sum_db(0, 50.0) == 50.0

    def test_both_zero(self):
        """0 + 0 = 0."""
        assert energy_sum_db(0, 0) == 0.0

    def test_commutative(self):
        """합산은 교환법칙이 성립해야 한다."""
        assert abs(energy_sum_db(55, 65) - energy_sum_db(65, 55)) < 0.001

    def test_large_difference(self):
        """큰 차이(20dB 이상)이면 큰 값과 거의 같아야 한다."""
        result = energy_sum_db(80.0, 50.0)
        assert abs(result - 80.0) < 0.1


# ════════════════════════════════════════════
# 5. NoisePropagationModel 통합 테스트
# ════════════════════════════════════════════

class TestNoisePropagationModel:
    """소음 전파 모델 클래스 테스트."""

    def setup_method(self):
        self.model = NoisePropagationModel()

    def test_model_info(self):
        """모델 정보 확인."""
        info = self.model.get_model_info()
        assert info.name == "noise_propagation"
        assert "noise_vibration" in info.applicable_sections

    def test_required_inputs(self):
        """입력 파라미터 목록 확인."""
        inputs = self.model.get_required_inputs()
        names = [inp.name for inp in inputs]
        assert "source_type" in names
        assert "sound_power_level" in names
        assert "barrier_height" in names
        assert "receiver_height" in names

    def test_predict_default_point_source(self):
        """기본 파라미터(점음원)로 예측이 정상 동작하는지 확인."""
        result = self.model.predict(parameters={})
        assert result.section_key == "noise_vibration"
        assert result.model_name == "noise_propagation"
        # 주간 + 야간 × 6거리 = 12
        assert len(result.predictions) == 2 * len(NOISE_DISTANCES)
        assert result.summary
        assert result.assumptions
        assert result.limitations

    def test_predict_line_source(self):
        """선음원(도로) 예측."""
        result = self.model.predict(
            parameters={"source_type": "line", "sound_power_level": 75.0}
        )
        assert result.input_parameters["source_type"] == "line"
        assert len(result.predictions) == 2 * len(NOISE_DISTANCES)

    def test_predict_with_project_type_road(self):
        """road 사업유형 → 선음원 자동 선택."""
        result = self.model.predict(parameters={"project_type": "road"})
        assert result.input_parameters["source_type"] == "line"

    def test_predict_with_project_type_industrial(self):
        """industrial 사업유형 → 점음원, Lw=100."""
        result = self.model.predict(parameters={"project_type": "industrial"})
        assert result.input_parameters["source_type"] == "point"
        assert result.input_parameters["sound_power_level"] == 100.0

    def test_predict_with_background_noise(self):
        """배경 소음 데이터 합산."""
        bg = {"소음_Leq_주간": 52.0, "소음_Leq_야간": 40.0}
        result = self.model.predict(parameters={}, background_data=bg)

        day_items = [p for p in result.predictions if p.pollutant == "소음_Leq_주간"]
        for p in day_items:
            assert p.background_concentration == 52.0
            # 합산값은 배경/예측 각각보다 커야 함
            assert p.total_concentration >= p.background_concentration
            assert p.total_concentration >= p.predicted_concentration

    def test_exceeds_standard_near_distance(self):
        """가까운 거리에서 환경기준 초과 판정."""
        result = self.model.predict(
            parameters={"sound_power_level": 100.0},
            background_data={"소음_Leq_주간": 50.0, "소음_Leq_야간": 40.0},
        )
        night_items = [p for p in result.predictions if p.pollutant == "소음_Leq_야간"]
        exceeded = [p for p in night_items if p.exceeds_standard]
        assert len(exceeded) > 0, "야간 가까운 거리에서 초과가 있어야 한다"

    def test_barrier_reduces_level(self):
        """차음벽이 소음도를 낮추는지 확인."""
        result_no_barrier = self.model.predict(
            parameters={"sound_power_level": 95.0, "barrier_height": 0.0}
        )
        result_with_barrier = self.model.predict(
            parameters={"sound_power_level": 95.0, "barrier_height": 5.0}
        )

        # 동일 거리에서 차음벽 유무 비교
        for dist in NOISE_DISTANCES:
            no_b = [
                p for p in result_no_barrier.predictions
                if p.pollutant == "소음_Leq_주간" and p.distance_m == dist
            ][0]
            with_b = [
                p for p in result_with_barrier.predictions
                if p.pollutant == "소음_Leq_주간" and p.distance_m == dist
            ][0]
            assert with_b.predicted_concentration <= no_b.predicted_concentration, (
                f"{dist}m에서 차음벽이 소음을 낮추지 못함"
            )

    def test_all_distances_present(self):
        """모든 예측 거리에 주간/야간 결과가 있어야 한다."""
        result = self.model.predict(parameters={})
        for period in ["소음_Leq_주간", "소음_Leq_야간"]:
            distances = sorted(
                p.distance_m for p in result.predictions if p.pollutant == period
            )
            assert distances == sorted(NOISE_DISTANCES)

    def test_custom_sound_power_overrides_default(self):
        """사용자 지정 음향파워레벨이 기본값을 재정의하는지 확인."""
        result = self.model.predict(
            parameters={"project_type": "housing", "sound_power_level": 105.0}
        )
        assert result.input_parameters["sound_power_level"] == 105.0

    def test_summary_contains_key_info(self):
        """요약 텍스트에 핵심 정보가 포함되는지 확인."""
        result = self.model.predict(
            parameters={"project_type": "power_plant"}
        )
        assert "소음" in result.summary
        assert "dB" in result.summary


# ════════════════════════════════════════════
# 6. 수질 혼합 모델 — 혼합 계산 테스트
# ════════════════════════════════════════════

class TestCompleteMixing:
    """완전혼합 희석 계산 테스트."""

    def test_simple_dilution(self):
        """간단한 희석 계산 검증.

        하천 10 m³/s × 2 mg/L + 방류 1 m³/s × 30 mg/L
        = (20 + 30) / 11 ≈ 4.545 mg/L
        """
        result = complete_mixing_concentration(10.0, 2.0, 1.0, 30.0)
        expected = (10.0 * 2.0 + 1.0 * 30.0) / 11.0
        assert abs(result - expected) < 0.001

    def test_zero_discharge(self):
        """방류량 0이면 하천 농도 유지."""
        result = complete_mixing_concentration(10.0, 5.0, 0.0, 30.0)
        assert abs(result - 5.0) < 0.001

    def test_zero_river_flow(self):
        """하천 유량 0이면 방류수 농도."""
        result = complete_mixing_concentration(0.0, 0.0, 1.0, 30.0)
        assert abs(result - 30.0) < 0.001

    def test_both_zero_flow(self):
        """양쪽 유량 모두 0이면 0 반환."""
        assert complete_mixing_concentration(0.0, 0.0, 0.0, 30.0) == 0.0

    def test_equal_concentration(self):
        """하천과 방류수 농도가 같으면 혼합 후도 같아야 한다."""
        result = complete_mixing_concentration(5.0, 10.0, 2.0, 10.0)
        assert abs(result - 10.0) < 0.001

    def test_high_dilution_ratio(self):
        """하천 유량이 매우 크면 방류 영향이 미미해야 한다.

        유량비 1:1000 → 혼합 농도 ≈ 하천 농도
        """
        result = complete_mixing_concentration(1000.0, 2.0, 1.0, 30.0)
        assert abs(result - 2.0) < 0.1

    def test_low_dilution_ratio(self):
        """하천 유량이 작으면 방류 영향이 커야 한다.

        유량비 1:1 → (2+30)/2 = 16 mg/L
        """
        result = complete_mixing_concentration(1.0, 2.0, 1.0, 30.0)
        expected = (1.0 * 2.0 + 1.0 * 30.0) / 2.0
        assert abs(result - expected) < 0.001

    def test_mixing_concentration_between_inputs(self):
        """혼합 농도는 항상 두 입력 농도 사이에 있어야 한다."""
        C_mix = complete_mixing_concentration(5.0, 3.0, 1.0, 30.0)
        assert 3.0 <= C_mix <= 30.0


# ════════════════════════════════════════════
# 7. WaterMixingModel 통합 테스트
# ════════════════════════════════════════════

class TestWaterMixingModel:
    """수질 혼합 모델 클래스 테스트."""

    def setup_method(self):
        self.model = WaterMixingModel()

    def test_model_info(self):
        """모델 정보 확인."""
        info = self.model.get_model_info()
        assert info.name == "water_mixing"
        assert "water_quality" in info.applicable_sections

    def test_required_inputs(self):
        """입력 파라미터 목록 확인."""
        inputs = self.model.get_required_inputs()
        names = [inp.name for inp in inputs]
        assert "river_flow" in names
        assert "discharge_flow" in names
        assert "discharge_bod" in names

    def test_predict_default_params(self):
        """기본 파라미터로 예측 정상 동작."""
        result = self.model.predict(parameters={})
        assert result.section_key == "water_quality"
        assert result.model_name == "water_mixing"
        assert len(result.predictions) == len(WATER_TARGET_POLLUTANTS)
        assert result.summary
        assert result.assumptions
        assert result.limitations

    def test_predict_with_background_data(self):
        """배경 수질 데이터가 반영되는지 확인."""
        bg = {"BOD": 2.5, "COD": 4.0, "SS": 10.0, "T-N": 3.0, "T-P": 0.1}
        result = self.model.predict(parameters={}, background_data=bg)

        bod_item = [p for p in result.predictions if p.pollutant == "BOD"][0]
        assert bod_item.background_concentration == 2.5
        # 혼합 농도는 배경과 방류수 사이
        assert bod_item.total_concentration >= 2.5
        assert bod_item.total_concentration <= DISCHARGE_STANDARDS["BOD"]

    def test_predict_without_background(self):
        """배경 없이 예측하면 하천 농도=0."""
        result = self.model.predict(parameters={})
        for p in result.predictions:
            assert p.background_concentration == 0.0

    def test_project_type_discharge_flow(self):
        """사업유형에 따른 기본 방류량이 적용되는지 확인."""
        result_ind = self.model.predict(parameters={"project_type": "industrial"})
        result_pwr = self.model.predict(parameters={"project_type": "power_plant"})
        # industrial(0.1) > power_plant(0.01)
        assert result_ind.input_parameters["discharge_flow"] > \
               result_pwr.input_parameters["discharge_flow"]

    def test_custom_discharge_overrides(self):
        """사용자 지정 방류수 농도가 기본값을 재정의하는지 확인."""
        result = self.model.predict(
            parameters={"discharge_bod": 10.0},
            background_data={"BOD": 2.0},
        )
        bod_item = [p for p in result.predictions if p.pollutant == "BOD"][0]
        # 방류 농도 = 10, 기본 30이 아닌 사용자 값
        assert bod_item.predicted_concentration == 10.0

    def test_exceeds_standard_detection(self):
        """환경기준 초과 판정.

        하천 BOD=4.5, 방류 BOD=30, 유량비가 크면 혼합 > 5.0
        """
        result = self.model.predict(
            parameters={
                "river_flow": 1.0,
                "discharge_flow": 0.5,
            },
            background_data={"BOD": 4.5},
        )
        bod_item = [p for p in result.predictions if p.pollutant == "BOD"][0]
        # (1.0*4.5 + 0.5*30) / 1.5 = 19.5/1.5 = 13.0 > 5.0
        assert bod_item.exceeds_standard

    def test_no_exceed_with_high_dilution(self):
        """희석률이 높으면 기준 초과가 없어야 한다."""
        result = self.model.predict(
            parameters={
                "river_flow": 100.0,
                "discharge_flow": 0.01,
            },
            background_data={"BOD": 1.0, "COD": 2.0, "SS": 5.0, "T-P": 0.05},
        )
        for p in result.predictions:
            if p.standard_value is not None:
                assert not p.exceeds_standard, f"{p.pollutant} 초과 발생"

    def test_tn_no_standard(self):
        """T-N은 하천 환경기준이 없으므로 exceeds_standard=False."""
        result = self.model.predict(parameters={})
        tn_item = [p for p in result.predictions if p.pollutant == "T-N"][0]
        assert tn_item.standard_value is None
        assert not tn_item.exceeds_standard

    def test_all_pollutants_present(self):
        """모든 대상 오염물질에 대한 결과가 있어야 한다."""
        result = self.model.predict(parameters={})
        pollutants = [p.pollutant for p in result.predictions]
        for target in WATER_TARGET_POLLUTANTS:
            assert target in pollutants

    def test_custom_river_flow(self):
        """사용자 지정 하천 유량이 적용되는지 확인."""
        result = self.model.predict(parameters={"river_flow": 50.0})
        assert result.input_parameters["river_flow"] == 50.0

    def test_custom_discharge_flow(self):
        """사용자 지정 방류량이 적용되는지 확인."""
        result = self.model.predict(parameters={"discharge_flow": 0.5})
        assert result.input_parameters["discharge_flow"] == 0.5

    def test_summary_contains_key_info(self):
        """요약 텍스트에 핵심 정보가 포함되는지 확인."""
        result = self.model.predict(parameters={"project_type": "industrial"})
        assert "혼합" in result.summary
        assert "BOD" in result.summary

    def test_mixing_formula_verification(self):
        """혼합 계산 공식이 모델 내부에서 올바르게 적용되는지 확인.

        river_flow=10, discharge_flow=1
        bg BOD=2.0, discharge BOD=30
        expected: (10*2+1*30)/11 ≈ 4.545
        """
        result = self.model.predict(
            parameters={"river_flow": 10.0, "discharge_flow": 1.0},
            background_data={"BOD": 2.0},
        )
        bod_item = [p for p in result.predictions if p.pollutant == "BOD"][0]
        expected = (10.0 * 2.0 + 1.0 * 30.0) / 11.0
        assert abs(bod_item.total_concentration - expected) < 0.01


# ════════════════════════════════════════════
# 8. 기본값 테스트
# ════════════════════════════════════════════

class TestNoiseDefaults:
    """소음 사업유형별 기본값 테스트."""

    def test_power_plant_defaults(self):
        """발전소 기본값: 점음원, 95dB."""
        d = DEFAULT_SOURCE_PARAMS["power_plant"]
        assert d["source_type"] == "point"
        assert d["sound_power_level"] == 95.0

    def test_road_defaults(self):
        """도로 기본값: 선음원, 75dB/m."""
        d = DEFAULT_SOURCE_PARAMS["road"]
        assert d["source_type"] == "line"
        assert d["sound_power_level"] == 75.0

    def test_housing_defaults(self):
        """주거 기본값: 점음원, 90dB."""
        d = DEFAULT_SOURCE_PARAMS["housing"]
        assert d["source_type"] == "point"
        assert d["sound_power_level"] == 90.0

    def test_industrial_defaults(self):
        """산업 기본값: 점음원, 100dB."""
        d = DEFAULT_SOURCE_PARAMS["industrial"]
        assert d["source_type"] == "point"
        assert d["sound_power_level"] == 100.0

    def test_noise_standards(self):
        """소음환경기준 값 확인."""
        assert NOISE_STANDARDS["주간"] == 55.0
        assert NOISE_STANDARDS["야간"] == 45.0


class TestWaterDefaults:
    """수질 사업유형별 기본값 테스트."""

    def test_discharge_standards(self):
        """방류수 수질기준 확인."""
        assert DISCHARGE_STANDARDS["BOD"] == 30.0
        assert DISCHARGE_STANDARDS["COD"] == 40.0
        assert DISCHARGE_STANDARDS["SS"] == 30.0
        assert DISCHARGE_STANDARDS["T-N"] == 60.0
        assert DISCHARGE_STANDARDS["T-P"] == 8.0

    def test_default_discharge_flows(self):
        """사업유형별 기본 방류량 확인."""
        assert DEFAULT_DISCHARGE_FLOW["power_plant"] == 0.01
        assert DEFAULT_DISCHARGE_FLOW["industrial"] == 0.1
        assert DEFAULT_DISCHARGE_FLOW["housing"] == 0.05

    def test_default_river_flow(self):
        """기본 하천 유량 확인."""
        assert DEFAULT_RIVER_FLOW == 1.0

    def test_water_pollutant_info(self):
        """수질 오염물질 정보 완전성 확인."""
        for poll in WATER_TARGET_POLLUTANTS:
            info = WATER_POLLUTANT_INFO[poll]
            assert "unit" in info
            assert "standard" in info
            assert "description" in info


# ════════════════════════════════════════════
# 9. 레지스트리 확장 테스트
# ════════════════════════════════════════════

class TestRegistryExtended:
    """새 모델의 레지스트리 등록 테스트."""

    def test_noise_model_registered(self):
        """소음 전파 모델이 레지스트리에 등록되어 있어야 한다."""
        model = get_model("noise_propagation")
        assert model is not None
        assert isinstance(model, NoisePropagationModel)

    def test_water_model_registered(self):
        """수질 혼합 모델이 레지스트리에 등록되어 있어야 한다."""
        model = get_model("water_mixing")
        assert model is not None
        assert isinstance(model, WaterMixingModel)

    def test_noise_section_mapping(self):
        """noise_vibration 섹션에 소음 모델이 매핑되어 있어야 한다."""
        models = get_models_for_section("noise_vibration")
        assert len(models) >= 1
        assert isinstance(models[0], NoisePropagationModel)

    def test_water_section_mapping(self):
        """water_quality 섹션에 수질 모델이 매핑되어 있어야 한다."""
        models = get_models_for_section("water_quality")
        assert len(models) >= 1
        assert isinstance(models[0], WaterMixingModel)

    def test_default_model_for_noise(self):
        """noise_vibration의 기본 모델 확인."""
        model = get_default_model_for_section("noise_vibration")
        assert model is not None
        assert model.get_model_info().name == "noise_propagation"

    def test_default_model_for_water(self):
        """water_quality의 기본 모델 확인."""
        model = get_default_model_for_section("water_quality")
        assert model is not None
        assert model.get_model_info().name == "water_mixing"

    def test_list_models_includes_new(self):
        """모델 목록에 새 모델이 포함되어 있어야 한다."""
        models = list_models()
        names = [m.name for m in models]
        assert "noise_propagation" in names
        assert "water_mixing" in names
        assert len(models) >= 3


# ════════════════════════════════════════════
# 10. API 엔드포인트 테스트
# ════════════════════════════════════════════

class TestPredictionAPIExtended:
    """새 모델의 API 엔드포인트 테스트."""

    @pytest.fixture
    def client(self):
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_prediction_models_list_includes_new(self, client):
        """GET /prediction-models — 새 모델이 목록에 포함."""
        async with client as c:
            resp = await c.get("/api/v1/prediction-models")
        assert resp.status_code == 200
        data = resp.json()
        names = [m["name"] for m in data]
        assert "noise_propagation" in names
        assert "water_mixing" in names

    @pytest.mark.asyncio
    async def test_noise_model_has_inputs(self, client):
        """소음 모델의 입력 파라미터가 포함되는지 확인."""
        async with client as c:
            resp = await c.get("/api/v1/prediction-models")
        data = resp.json()
        noise_model = [m for m in data if m["name"] == "noise_propagation"][0]
        input_names = [inp["name"] for inp in noise_model["required_inputs"]]
        assert "source_type" in input_names
        assert "sound_power_level" in input_names
        assert "barrier_height" in input_names

    @pytest.mark.asyncio
    async def test_water_model_has_inputs(self, client):
        """수질 모델의 입력 파라미터가 포함되는지 확인."""
        async with client as c:
            resp = await c.get("/api/v1/prediction-models")
        data = resp.json()
        water_model = [m for m in data if m["name"] == "water_mixing"][0]
        input_names = [inp["name"] for inp in water_model["required_inputs"]]
        assert "river_flow" in input_names
        assert "discharge_flow" in input_names
        assert "discharge_bod" in input_names

    def test_noise_section_has_default_model(self):
        """noise_vibration 섹션에 기본 모델이 있는지 확인 (API 404는 기존 테스트에서 커버)."""
        from app.services.prediction.registry import get_default_model_for_section
        model = get_default_model_for_section("noise_vibration")
        assert model is not None

    def test_water_section_has_default_model(self):
        """water_quality 섹션에 기본 모델이 있는지 확인 (API 404는 기존 테스트에서 커버)."""
        from app.services.prediction.registry import get_default_model_for_section
        model = get_default_model_for_section("water_quality")
        assert model is not None
