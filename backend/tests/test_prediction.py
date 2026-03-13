"""예측 모듈 테스트.

가우시안 플룸 계산 정확성, 확산계수 계산, API 엔드포인트, 기본값 적용을 검증한다.
"""

from __future__ import annotations

import math
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.prediction.air_dispersion import (
    DEFAULT_EMISSIONS,
    DEFAULT_STACK_HEIGHT,
    DEFAULT_WIND_SPEED,
    POLLUTANT_INFO,
    PREDICTION_DISTANCES,
    AirDispersionModel,
    PG_COEFFICIENTS,
    compute_sigma_y,
    compute_sigma_z,
    gaussian_plume_ground_concentration,
)
from app.services.prediction.base import (
    BasePredictionModel,
    InputParameter,
    ModelInfo,
    PredictionResult,
)
from app.services.prediction.registry import (
    get_default_model_for_section,
    get_model,
    get_models_for_section,
    list_models,
)


# ────────────────────────────────────────────
# 확산계수 계산 테스트
# ────────────────────────────────────────────

class TestSigmaCoefficients:
    """Pasquill-Gifford 확산계수 σy, σz 계산 테스트."""

    def test_sigma_y_at_zero_distance(self):
        """풍하거리 0에서 σy는 0이어야 한다."""
        assert compute_sigma_y(0, "D") == 0.0

    def test_sigma_z_at_zero_distance(self):
        """풍하거리 0에서 σz는 0이어야 한다."""
        assert compute_sigma_z(0, "D") == 0.0

    def test_sigma_y_negative_distance(self):
        """음수 거리에서 σy는 0이어야 한다."""
        assert compute_sigma_y(-1, "D") == 0.0

    def test_sigma_z_negative_distance(self):
        """음수 거리에서 σz는 0이어야 한다."""
        assert compute_sigma_z(-1, "D") == 0.0

    def test_sigma_y_increases_with_distance(self):
        """σy는 풍하거리가 증가하면 증가해야 한다."""
        for cls in PG_COEFFICIENTS:
            s1 = compute_sigma_y(0.1, cls)
            s2 = compute_sigma_y(1.0, cls)
            s3 = compute_sigma_y(5.0, cls)
            assert s1 < s2 < s3, f"안정도 {cls}에서 σy가 거리에 비례하지 않음"

    def test_sigma_z_increases_with_distance(self):
        """σz는 풍하거리가 증가하면 증가해야 한다."""
        for cls in PG_COEFFICIENTS:
            s1 = compute_sigma_z(0.1, cls)
            s2 = compute_sigma_z(1.0, cls)
            s3 = compute_sigma_z(5.0, cls)
            assert s1 < s2 < s3, f"안정도 {cls}에서 σz가 거리에 비례하지 않음"

    def test_sigma_y_unstable_wider_than_stable(self):
        """불안정 등급(A)의 σy가 안정 등급(F)보다 커야 한다."""
        x_km = 1.0
        assert compute_sigma_y(x_km, "A") > compute_sigma_y(x_km, "F")

    def test_sigma_z_unstable_wider_than_stable(self):
        """불안정 등급(A)의 σz가 안정 등급(F)보다 커야 한다."""
        x_km = 1.0
        assert compute_sigma_z(x_km, "A") > compute_sigma_z(x_km, "F")

    @pytest.mark.parametrize("stability", list(PG_COEFFICIENTS.keys()))
    def test_sigma_y_positive_for_all_classes(self, stability):
        """모든 안정도 등급에서 σy는 양수여야 한다 (x > 0)."""
        assert compute_sigma_y(1.0, stability) > 0

    @pytest.mark.parametrize("stability", list(PG_COEFFICIENTS.keys()))
    def test_sigma_z_positive_for_all_classes(self, stability):
        """모든 안정도 등급에서 σz는 양수여야 한다 (x > 0)."""
        assert compute_sigma_z(1.0, stability) > 0

    def test_sigma_y_formula_d_class_1km(self):
        """D등급 1km에서 σy 수동 계산과 일치하는지 검증."""
        # σy = a * x^b = 68.0 * 1.0^0.894 = 68.0
        expected = 68.0 * (1.0 ** 0.894)
        actual = compute_sigma_y(1.0, "D")
        assert abs(actual - expected) < 1e-6

    def test_sigma_z_formula_d_class_1km(self):
        """D등급 1km에서 σz 수동 계산과 일치하는지 검증."""
        # σz = c * x^d = 33.2 * 1.0^0.725 = 33.2
        expected = 33.2 * (1.0 ** 0.725)
        actual = compute_sigma_z(1.0, "D")
        assert abs(actual - expected) < 1e-6


# ────────────────────────────────────────────
# 가우시안 플룸 농도 계산 테스트
# ────────────────────────────────────────────

class TestGaussianPlume:
    """가우시안 플룸 모델 지표면 농도 계산 테스트."""

    def test_zero_emission(self):
        """배출량 0이면 농도도 0이어야 한다."""
        assert gaussian_plume_ground_concentration(Q=0, u=3, H=30, x_m=1000) == 0.0

    def test_zero_wind_speed(self):
        """풍속 0이면 농도 0을 반환해야 한다 (0으로 나누기 방지)."""
        assert gaussian_plume_ground_concentration(Q=1, u=0, H=30, x_m=1000) == 0.0

    def test_zero_distance(self):
        """풍하거리 0이면 농도 0이어야 한다."""
        assert gaussian_plume_ground_concentration(Q=1, u=3, H=30, x_m=0) == 0.0

    def test_negative_distance(self):
        """음수 거리이면 농도 0이어야 한다."""
        assert gaussian_plume_ground_concentration(Q=1, u=3, H=30, x_m=-100) == 0.0

    def test_concentration_positive(self):
        """정상 조건에서 농도는 양수여야 한다."""
        c = gaussian_plume_ground_concentration(Q=1, u=3, H=30, x_m=1000)
        assert c > 0

    def test_concentration_decreases_with_distance(self):
        """일정 거리 이후 농도가 감소해야 한다.

        가우시안 플룸에서 지표면 농도는 특정 거리에서 최대가 된 뒤 감소한다.
        충분히 먼 거리에서는 반드시 감소해야 한다.
        """
        c_1km = gaussian_plume_ground_concentration(Q=1, u=3, H=30, x_m=1000)
        c_5km = gaussian_plume_ground_concentration(Q=1, u=3, H=30, x_m=5000)
        c_10km = gaussian_plume_ground_concentration(Q=1, u=3, H=30, x_m=10000)
        # 5km~10km 구간에서는 반드시 감소
        assert c_10km < c_5km

    def test_higher_emission_higher_concentration(self):
        """배출량이 높으면 농도도 높아야 한다."""
        c_low = gaussian_plume_ground_concentration(Q=0.5, u=3, H=30, x_m=1000)
        c_high = gaussian_plume_ground_concentration(Q=2.0, u=3, H=30, x_m=1000)
        assert c_high > c_low

    def test_concentration_proportional_to_emission(self):
        """농도는 배출량에 정비례해야 한다."""
        c1 = gaussian_plume_ground_concentration(Q=1, u=3, H=30, x_m=1000)
        c2 = gaussian_plume_ground_concentration(Q=2, u=3, H=30, x_m=1000)
        assert abs(c2 / c1 - 2.0) < 1e-6

    def test_higher_wind_lower_concentration(self):
        """풍속이 빠르면 농도가 낮아야 한다."""
        c_low_wind = gaussian_plume_ground_concentration(Q=1, u=2, H=30, x_m=1000)
        c_high_wind = gaussian_plume_ground_concentration(Q=1, u=5, H=30, x_m=1000)
        assert c_high_wind < c_low_wind

    def test_higher_stack_lower_surface_concentration(self):
        """굴뚝이 높으면 지표면 농도가 낮아야 한다 (같은 거리)."""
        c_low_stack = gaussian_plume_ground_concentration(Q=1, u=3, H=20, x_m=1000)
        c_high_stack = gaussian_plume_ground_concentration(Q=1, u=3, H=50, x_m=1000)
        assert c_high_stack < c_low_stack

    def test_manual_calculation_d_class(self):
        """D등급 1km에서 수동 계산과 일치하는지 검증.

        Q=1 g/s, u=3 m/s, H=30m, x=1000m (1km), 안정도 D
        σy = 68.0 * 1^0.894 = 68.0 m
        σz = 33.2 * 1^0.725 = 33.2 m
        C = (1 / (π * 68 * 33.2 * 3)) * exp(-30²/(2*33.2²)) * 1e6
        """
        Q, u, H, x = 1.0, 3.0, 30.0, 1000.0
        sigma_y = 68.0
        sigma_z = 33.2

        expected_g = (Q / (math.pi * sigma_y * sigma_z * u)) * math.exp(
            -(H ** 2) / (2 * sigma_z ** 2)
        )
        expected_ug = expected_g * 1e6

        actual = gaussian_plume_ground_concentration(Q=Q, u=u, H=H, x_m=x, stability_class="D")
        assert abs(actual - expected_ug) < 0.1, (
            f"수동 계산 {expected_ug:.2f} vs 함수 {actual:.2f}"
        )

    @pytest.mark.parametrize("stability", list(PG_COEFFICIENTS.keys()))
    def test_all_stability_classes_produce_positive(self, stability):
        """모든 안정도 등급에서 양수 농도가 나와야 한다."""
        c = gaussian_plume_ground_concentration(
            Q=1, u=3, H=30, x_m=1000, stability_class=stability
        )
        assert c > 0


# ────────────────────────────────────────────
# AirDispersionModel 통합 테스트
# ────────────────────────────────────────────

class TestAirDispersionModel:
    """대기 확산 모델 클래스 테스트."""

    def setup_method(self):
        self.model = AirDispersionModel()

    def test_model_info(self):
        """모델 정보가 올바르게 반환되는지 확인."""
        info = self.model.get_model_info()
        assert info.name == "gaussian_plume"
        assert "air_quality" in info.applicable_sections
        assert info.display_name

    def test_required_inputs(self):
        """필수 입력 파라미터 목록이 반환되는지 확인."""
        inputs = self.model.get_required_inputs()
        assert len(inputs) >= 5
        names = [inp.name for inp in inputs]
        assert "stack_height" in names
        assert "wind_speed" in names
        assert "stability_class" in names

    def test_predict_default_params(self):
        """기본 파라미터로 예측이 정상 동작하는지 확인."""
        result = self.model.predict(parameters={})
        assert result.section_key == "air_quality"
        assert result.model_name == "gaussian_plume"
        assert len(result.predictions) > 0
        assert result.summary
        assert result.assumptions
        assert result.limitations

    def test_predict_with_project_type(self):
        """사업유형 지정 시 해당 기본값이 적용되는지 확인.

        power_plant과 industrial을 같은 굴뚝 높이로 비교하면
        industrial의 배출량(1.0g/s)이 power_plant(0.5g/s)보다 크므로
        농도도 커야 한다.
        """
        H = 30.0  # 동일 굴뚝 높이로 배출량 차이만 확인
        result_power = self.model.predict(
            parameters={"project_type": "power_plant", "stack_height": H}
        )
        result_industrial = self.model.predict(
            parameters={"project_type": "industrial", "stack_height": H}
        )

        pm10_power = [
            p for p in result_power.predictions
            if p.pollutant == "PM10" and p.distance_m == 1000
        ]
        pm10_ind = [
            p for p in result_industrial.predictions
            if p.pollutant == "PM10" and p.distance_m == 1000
        ]
        assert len(pm10_power) == 1
        assert len(pm10_ind) == 1
        # industrial(1.0g/s) > power_plant(0.5g/s) → 농도도 industrial이 더 높아야 함
        assert pm10_ind[0].predicted_concentration > pm10_power[0].predicted_concentration

    def test_predict_with_custom_emissions(self):
        """사용자 지정 배출량이 기본값보다 우선 적용되는지 확인."""
        custom_q = 5.0
        result = self.model.predict(
            parameters={"emission_rate_pm10": custom_q, "project_type": "power_plant"}
        )
        pm10_items = [p for p in result.predictions if p.pollutant == "PM10"]
        assert len(pm10_items) > 0

        # 배출량이 power_plant 기본(0.5)보다 10배이므로 농도도 10배
        result_default = self.model.predict(
            parameters={"project_type": "power_plant"}
        )
        pm10_default = [
            p for p in result_default.predictions
            if p.pollutant == "PM10" and p.distance_m == 1000
        ][0]
        pm10_custom = [
            p for p in pm10_items
            if p.distance_m == 1000
        ][0]
        ratio = pm10_custom.predicted_concentration / pm10_default.predicted_concentration
        assert abs(ratio - 10.0) < 0.01

    def test_predict_with_background_data(self):
        """배경 농도 데이터 합산이 정상 동작하는지 확인."""
        bg = {"PM10": 45.0, "PM2.5": 22.0, "NO2": 30.0, "SO2": 5.0}
        result = self.model.predict(parameters={}, background_data=bg)

        for p in result.predictions:
            expected_total = p.background_concentration + p.predicted_concentration
            assert abs(p.total_concentration - expected_total) < 0.01

        # 배경 농도가 반영되었는지 확인
        pm10_item = [
            p for p in result.predictions
            if p.pollutant == "PM10" and p.distance_m == 1000
        ][0]
        assert pm10_item.background_concentration == 45.0

    def test_predict_without_background_data(self):
        """배경 농도 없이 예측하면 배경=0이어야 한다."""
        result = self.model.predict(parameters={})
        for p in result.predictions:
            assert p.background_concentration == 0.0
            assert p.total_concentration == p.predicted_concentration

    def test_exceeds_standard_detection(self):
        """환경기준 초과 시 exceeds_standard=True 판정."""
        # 매우 높은 배출량 → 기준 초과 유발
        result = self.model.predict(
            parameters={"emission_rate_pm10": 100.0},
            background_data={"PM10": 40.0},
        )
        pm10_items = [p for p in result.predictions if p.pollutant == "PM10"]
        # 가까운 거리에서 기준 초과가 있어야 함
        exceeded = [p for p in pm10_items if p.exceeds_standard]
        assert len(exceeded) > 0

    def test_no_exceed_with_low_emission(self):
        """배출량이 매우 낮으면 기준 초과가 없어야 한다."""
        result = self.model.predict(
            parameters={"emission_rate_pm10": 0.001},
            background_data={"PM10": 10.0},
        )
        pm10_items = [p for p in result.predictions if p.pollutant == "PM10"]
        exceeded = [p for p in pm10_items if p.exceeds_standard]
        assert len(exceeded) == 0

    def test_all_prediction_distances_present(self):
        """모든 예측 거리에 대한 결과가 있어야 한다."""
        result = self.model.predict(parameters={})
        for pollutant in ["PM10", "PM2.5", "NO2", "SO2"]:
            distances = sorted(
                p.distance_m for p in result.predictions if p.pollutant == pollutant
            )
            assert distances == sorted(PREDICTION_DISTANCES)

    def test_predictions_count(self):
        """예측 결과 수 = 오염물질 4개 × 거리 6개 = 24."""
        result = self.model.predict(parameters={})
        assert len(result.predictions) == 4 * len(PREDICTION_DISTANCES)

    def test_invalid_stability_class_fallback(self):
        """유효하지 않은 안정도 등급은 D(중립)으로 대체."""
        result = self.model.predict(
            parameters={"stability_class": "X"}
        )
        assert "D" in result.input_parameters["stability_class"]

    def test_summary_contains_pollutant_info(self):
        """요약 텍스트에 오염물질 정보가 포함되어야 한다."""
        result = self.model.predict(
            parameters={"project_type": "power_plant"}
        )
        assert "PM10" in result.summary
        assert "가우시안 플룸" in result.summary

    def test_custom_wind_speed(self):
        """사용자 지정 풍속이 적용되는지 확인."""
        result = self.model.predict(parameters={"wind_speed": 5.0})
        assert result.input_parameters["wind_speed"] == 5.0

    def test_custom_stack_height(self):
        """사용자 지정 굴뚝 높이가 적용되는지 확인."""
        result = self.model.predict(parameters={"stack_height": 80.0})
        assert result.input_parameters["stack_height"] == 80.0


# ────────────────────────────────────────────
# 기본값 적용 테스트
# ────────────────────────────────────────────

class TestDefaults:
    """사업유형별 기본값 테스트."""

    def test_power_plant_emissions(self):
        """발전소 기본 배출량이 정의되어 있는지 확인."""
        em = DEFAULT_EMISSIONS["power_plant"]
        assert em["PM10"] == 0.5
        assert em["PM2.5"] == 0.3
        assert em["NO2"] == 1.0
        assert em["SO2"] == 0.5

    def test_industrial_emissions(self):
        """산업단지 기본 배출량이 정의되어 있는지 확인."""
        em = DEFAULT_EMISSIONS["industrial"]
        assert em["PM10"] == 1.0
        assert em["PM2.5"] == 0.5
        assert em["NO2"] == 2.0
        assert em["SO2"] == 1.0

    def test_other_types_half_of_power_plant(self):
        """기타 사업유형은 power_plant의 50%인지 확인."""
        pp = DEFAULT_EMISSIONS["power_plant"]
        for ptype in ("road", "railway", "housing", "airport", "port", "dam", "reclamation", "other"):
            em = DEFAULT_EMISSIONS[ptype]
            for poll in ("PM10", "PM2.5", "NO2", "SO2"):
                assert abs(em[poll] - pp[poll] * 0.5) < 1e-6, (
                    f"{ptype}/{poll}: {em[poll]} != {pp[poll] * 0.5}"
                )

    def test_stack_height_defaults(self):
        """기본 굴뚝 높이가 사업유형별로 올바르게 설정되는지 확인."""
        assert DEFAULT_STACK_HEIGHT["power_plant"] == 50.0
        assert DEFAULT_STACK_HEIGHT["industrial"] == 30.0
        for ptype in ("road", "railway", "housing", "airport", "port"):
            assert DEFAULT_STACK_HEIGHT[ptype] == 20.0

    def test_default_wind_speed(self):
        """기본 풍속이 3.0 m/s인지 확인."""
        assert DEFAULT_WIND_SPEED == 3.0

    def test_pollutant_info_complete(self):
        """모든 대상 오염물질의 정보가 정의되어 있는지 확인."""
        for poll in ("PM10", "PM2.5", "NO2", "SO2"):
            info = POLLUTANT_INFO[poll]
            assert "unit" in info
            assert "standard" in info
            assert info["standard"] > 0


# ────────────────────────────────────────────
# 레지스트리 테스트
# ────────────────────────────────────────────

class TestRegistry:
    """모델 레지스트리 테스트."""

    def test_get_model_exists(self):
        """등록된 모델을 정상 조회할 수 있어야 한다."""
        model = get_model("gaussian_plume")
        assert model is not None
        assert isinstance(model, AirDispersionModel)

    def test_get_model_not_exists(self):
        """미등록 모델은 None을 반환해야 한다."""
        model = get_model("nonexistent")
        assert model is None

    def test_list_models(self):
        """모델 목록이 1개 이상이어야 한다."""
        models = list_models()
        assert len(models) >= 1
        names = [m.name for m in models]
        assert "gaussian_plume" in names

    def test_get_models_for_section(self):
        """air_quality 섹션에 가우시안 플룸 모델이 등록되어 있어야 한다."""
        models = get_models_for_section("air_quality")
        assert len(models) >= 1
        assert isinstance(models[0], AirDispersionModel)

    def test_get_models_for_unknown_section(self):
        """미등록 섹션은 빈 목록을 반환해야 한다."""
        models = get_models_for_section("unknown_section")
        assert models == []

    def test_default_model_for_air_quality(self):
        """air_quality의 기본 모델이 가우시안 플룸이어야 한다."""
        model = get_default_model_for_section("air_quality")
        assert model is not None
        assert model.get_model_info().name == "gaussian_plume"

    def test_default_model_for_unknown_section(self):
        """미등록 섹션의 기본 모델은 None이어야 한다."""
        model = get_default_model_for_section("ecology")
        assert model is None


# ────────────────────────────────────────────
# API 엔드포인트 테스트
# ────────────────────────────────────────────

class TestPredictionAPI:
    """예측 API 엔드포인트 테스트."""

    @pytest.fixture
    def client(self):
        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_get_prediction_models(self, client):
        """GET /prediction-models — 모델 목록 조회."""
        async with client as c:
            resp = await c.get("/api/v1/prediction-models")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        model = data[0]
        assert model["name"] == "gaussian_plume"
        assert "display_name" in model
        assert "description" in model
        assert "required_inputs" in model
        assert len(model["required_inputs"]) > 0

    @pytest.mark.asyncio
    async def test_predict_nonexistent_project(self, client):
        """존재하지 않는 프로젝트 ID로 예측 시 404."""
        fake_id = str(uuid.uuid4())
        async with client as c:
            resp = await c.post(
                f"/api/v1/projects/{fake_id}/predict/air_quality",
                json={"parameters": {}},
            )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_predict_invalid_model(self, client):
        """존재하지 않는 모델명으로 예측 시 400 (프로젝트 존재 시).

        프로젝트가 없으면 404가 먼저 나오므로, 이 테스트는 모델 검증 로직을
        단위 테스트 수준에서 확인한다.
        """
        # 모델 자체 검증은 레지스트리 테스트에서 커버
        model = get_model("nonexistent_model")
        assert model is None

    @pytest.mark.asyncio
    async def test_predict_unsupported_section(self, client):
        """예측 모델이 없는 섹션에 대한 요청 시 400 (프로젝트 존재 시).

        프로젝트가 없으면 404가 먼저 나오므로, 레지스트리 수준에서 확인.
        """
        model = get_default_model_for_section("water_quality")
        assert model is None


# ────────────────────────────────────────────
# BasePredictionModel 추상 클래스 테스트
# ────────────────────────────────────────────

class TestBasePredictionModel:
    """BasePredictionModel 추상 클래스 검증."""

    def test_cannot_instantiate_directly(self):
        """추상 클래스를 직접 인스턴스화하면 TypeError가 발생해야 한다."""
        with pytest.raises(TypeError):
            BasePredictionModel()

    def test_subclass_must_implement_methods(self):
        """필수 메서드를 구현하지 않은 서브클래스는 인스턴스화 불가."""
        class IncompleteModel(BasePredictionModel):
            pass

        with pytest.raises(TypeError):
            IncompleteModel()

    def test_subclass_with_all_methods(self):
        """모든 필수 메서드를 구현한 서브클래스는 정상 인스턴스화."""
        class CompleteModel(BasePredictionModel):
            def predict(self, parameters, background_data=None):
                return PredictionResult(
                    section_key="test", model_name="test",
                    input_parameters=parameters,
                )

            def get_required_inputs(self):
                return []

            def get_model_info(self):
                return ModelInfo(
                    name="test", display_name="테스트",
                    description="테스트 모델",
                    applicable_sections=["test"],
                )

        model = CompleteModel()
        assert model.get_model_info().name == "test"
