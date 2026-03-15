"""대기 확산 예측 모델 — 가우시안 플룸.

Pasquill-Gifford 대기안정도 분류에 기반한 가우시안 플룸 모델로
점오염원(굴뚝)에서의 풍하거리별 지표면 오염물질 농도를 예측한다.

참조:
- Turner, D.B. (1970) "Workbook of Atmospheric Dispersion Estimates"
- Pasquill, F. (1961) "The estimation of the dispersion of windborne material"
- 환경부 「대기영향 예측기법 가이드라인」
"""

from __future__ import annotations

import math

from app.services.prediction.base import (
    BasePredictionModel,
    InputParameter,
    ModelInfo,
    PredictionItem,
    PredictionResult,
)


# ────────────────────────────────────────────
# 사업유형별 기본 배출량 (g/s)
# ────────────────────────────────────────────

DEFAULT_EMISSIONS: dict[str, dict[str, float]] = {
    "power_plant": {
        "PM10": 0.5, "PM2.5": 0.3, "NO2": 1.0, "SO2": 0.5,
    },
    "industrial": {
        "PM10": 1.0, "PM2.5": 0.5, "NO2": 2.0, "SO2": 1.0,
    },
}

# 기타 사업유형은 power_plant의 50% 수준
_DEFAULT_FACTOR = 0.5
for _ptype in ("road", "railway", "housing", "airport", "port", "dam", "reclamation", "other"):
    DEFAULT_EMISSIONS[_ptype] = {
        k: v * _DEFAULT_FACTOR
        for k, v in DEFAULT_EMISSIONS["power_plant"].items()
    }

# 기본 유효 굴뚝 높이 (m) — 사업유형별 현실적 배출원 높이
# road/railway: 차량 배기관 높이 (지면 배출원)
# housing: 아파트 보일러 배기구
# power_plant/industrial: 굴뚝
DEFAULT_STACK_HEIGHT: dict[str, float] = {
    "power_plant": 50.0,
    "industrial": 30.0,
    "road": 0.0,
    "railway": 3.0,
    "housing": 15.0,
    "airport": 5.0,
    "port": 10.0,
    "dam": 0.0,
    "reclamation": 5.0,
    "other": 10.0,
}

# 기본 풍속 (m/s)
DEFAULT_WIND_SPEED = 3.0

# 예측 대상 풍하거리 (m)
PREDICTION_DISTANCES = [100, 200, 500, 1000, 2000, 5000]

# 대상 오염물질
TARGET_POLLUTANTS = ["PM10", "PM2.5", "NO2", "SO2"]

# 오염물질별 단위 및 환경기준 (연평균, ug/m3 기준)
# NO2, SO2는 ppm 기준이지만 확산 모델은 ug/m3로 통일 후 변환
POLLUTANT_INFO: dict[str, dict] = {
    "PM10": {"unit": "ug/m3", "standard": 50.0},
    "PM2.5": {"unit": "ug/m3", "standard": 15.0},
    "NO2": {"unit": "ug/m3", "standard": 56.4},    # 0.03 ppm ≈ 56.4 ug/m3 (20°C, 1atm)
    "SO2": {"unit": "ug/m3", "standard": 52.4},    # 0.02 ppm ≈ 52.4 ug/m3 (20°C, 1atm)
}


# ────────────────────────────────────────────
# Pasquill-Gifford 확산계수
# ────────────────────────────────────────────
# σy = a * x^b  (x: 풍하거리 km)
# σz = c * x^d  (x: 풍하거리 km)
# 출처: Turner (1970), Briggs urban formulas 간소화

PG_COEFFICIENTS: dict[str, dict[str, float]] = {
    "A": {"a": 213.0, "b": 0.894, "c": 440.8, "d": 1.941},  # 매우 불안정
    "B": {"a": 156.0, "b": 0.894, "c": 106.6, "d": 1.149},  # 불안정
    "C": {"a": 104.0, "b": 0.894, "c": 61.0, "d": 0.911},   # 약간 불안정
    "D": {"a": 68.0,  "b": 0.894, "c": 33.2, "d": 0.725},   # 중립
    "E": {"a": 50.5,  "b": 0.894, "c": 22.8, "d": 0.678},   # 약간 안정
    "F": {"a": 34.0,  "b": 0.894, "c": 14.35, "d": 0.740},  # 안정
}

STABILITY_CLASS_NAMES: dict[str, str] = {
    "A": "매우 불안정 (강한 일사, 약풍)",
    "B": "불안정 (보통 일사, 약풍)",
    "C": "약간 불안정 (약한 일사, 약풍)",
    "D": "중립 (흐림, 보통풍)",
    "E": "약간 안정 (약한 야간냉각)",
    "F": "안정 (강한 야간냉각, 약풍)",
}


def compute_sigma_y(x_km: float, stability_class: str) -> float:
    """수평 확산계수 σy (m)를 계산한다.

    Args:
        x_km: 풍하거리 (km)
        stability_class: 대기안정도 등급 (A~F)

    Returns:
        σy (m)
    """
    if x_km <= 0:
        return 0.0
    coeff = PG_COEFFICIENTS[stability_class]
    return coeff["a"] * (x_km ** coeff["b"])


def compute_sigma_z(x_km: float, stability_class: str) -> float:
    """수직 확산계수 σz (m)를 계산한다.

    Args:
        x_km: 풍하거리 (km)
        stability_class: 대기안정도 등급 (A~F)

    Returns:
        σz (m)
    """
    if x_km <= 0:
        return 0.0
    coeff = PG_COEFFICIENTS[stability_class]
    return coeff["c"] * (x_km ** coeff["d"])


def gaussian_plume_ground_concentration(
    Q: float,
    u: float,
    H: float,
    x_m: float,
    stability_class: str = "D",
) -> float:
    """가우시안 플룸 모델로 지표면 중심선 농도를 계산한다.

    풍하거리 x, 수평 이탈 y=0, 지표면 z=0 에서의 농도.

    공식:
        C(x,0,0) = Q / (π * σy * σz * u) * exp(-H² / (2 * σz²))

    Args:
        Q: 배출량 (g/s)
        u: 풍속 (m/s)
        H: 유효 굴뚝 높이 (m)
        x_m: 풍하거리 (m)
        stability_class: 대기안정도 등급 (A~F)

    Returns:
        지표면 농도 (ug/m3)
    """
    if x_m <= 0 or u <= 0 or Q <= 0:
        return 0.0

    x_km = x_m / 1000.0
    sigma_y = compute_sigma_y(x_km, stability_class)
    sigma_z = compute_sigma_z(x_km, stability_class)

    if sigma_y <= 0 or sigma_z <= 0:
        return 0.0

    # 지표면 반사 포함 (z=0 일 때 반사항 = exp(-H²/(2σz²)) * 2 → 풍하 중심선에서 2배)
    # C = Q / (π * σy * σz * u) * exp(-H²/(2σz²))
    exponent = -(H ** 2) / (2.0 * sigma_z ** 2)
    concentration_g_per_m3 = (Q / (math.pi * sigma_y * sigma_z * u)) * math.exp(exponent)

    # g/m³ → ug/m³ (× 10^6)
    return concentration_g_per_m3 * 1e6


def _format_distance(distance_m: float) -> str:
    """거리를 사람이 읽기 쉬운 형태로 변환한다."""
    if distance_m >= 1000:
        km = distance_m / 1000
        return f"{km:g}km"
    return f"{distance_m:g}m"


class AirDispersionModel(BasePredictionModel):
    """대기 확산 예측 모델 (가우시안 플룸).

    점오염원에서의 대기오염물질 확산을 가우시안 플룸 모델로 예측한다.
    """

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name="gaussian_plume",
            display_name="가우시안 플룸 대기 확산 모델",
            description=(
                "Pasquill-Gifford 대기안정도 분류에 기반한 가우시안 플룸 모델. "
                "점오염원(굴뚝)에서의 풍하거리별 지표면 오염물질 농도를 예측한다. "
                "PM10, PM2.5, NO2, SO2에 대해 예측하며, "
                "기존 대기질 현황 데이터와 합산하여 사업 후 예상 농도를 산출한다."
            ),
            applicable_sections=["air_quality"],
        )

    def get_required_inputs(self) -> list[InputParameter]:
        return [
            InputParameter(
                name="project_type",
                display_name="사업 유형",
                unit="",
                default="other",
                required=False,
                description="사업유형별 기본 배출량 적용 (power_plant, industrial 등)",
            ),
            InputParameter(
                name="emission_rate_pm10",
                display_name="PM10 배출량",
                unit="g/s",
                default=None,
                required=False,
                description="PM10 배출량. 미입력 시 사업유형별 기본값 적용",
            ),
            InputParameter(
                name="emission_rate_pm25",
                display_name="PM2.5 배출량",
                unit="g/s",
                default=None,
                required=False,
                description="PM2.5 배출량. 미입력 시 사업유형별 기본값 적용",
            ),
            InputParameter(
                name="emission_rate_no2",
                display_name="NO2 배출량",
                unit="g/s",
                default=None,
                required=False,
                description="NO2 배출량. 미입력 시 사업유형별 기본값 적용",
            ),
            InputParameter(
                name="emission_rate_so2",
                display_name="SO2 배출량",
                unit="g/s",
                default=None,
                required=False,
                description="SO2 배출량. 미입력 시 사업유형별 기본값 적용",
            ),
            InputParameter(
                name="stack_height",
                display_name="굴뚝 높이",
                unit="m",
                default=None,
                required=False,
                description="유효 굴뚝 높이. 미입력 시 사업유형별 기본값 적용",
            ),
            InputParameter(
                name="wind_speed",
                display_name="풍속",
                unit="m/s",
                default=DEFAULT_WIND_SPEED,
                required=False,
                description="평균 풍속. 미입력 시 기후 데이터 또는 기본값(3.0 m/s) 적용",
            ),
            InputParameter(
                name="stability_class",
                display_name="대기안정도 등급",
                unit="",
                default="D",
                required=False,
                description="Pasquill-Gifford 안정도 등급 (A~F). 기본값: D(중립)",
            ),
        ]

    def predict(
        self,
        parameters: dict,
        background_data: dict[str, float] | None = None,
    ) -> PredictionResult:
        """대기 확산 예측을 실행한다.

        Args:
            parameters: 입력 파라미터 딕셔너리
            background_data: 배경 농도 (오염물질명 → 연평균 농도 ug/m3)
                             예: {"PM10": 45.0, "PM2.5": 22.0, "NO2": 30.0, "SO2": 5.0}
        """
        bg = background_data or {}
        project_type = parameters.get("project_type", "other")

        # 사업유형별 기본 배출량
        type_defaults = DEFAULT_EMISSIONS.get(project_type, DEFAULT_EMISSIONS["other"])

        # 개별 오염물질 배출량 — 직접 입력 우선, 없으면 기본값
        emissions: dict[str, float] = {}
        param_keys = {
            "PM10": "emission_rate_pm10",
            "PM2.5": "emission_rate_pm25",
            "NO2": "emission_rate_no2",
            "SO2": "emission_rate_so2",
        }
        for pollutant, param_key in param_keys.items():
            val = parameters.get(param_key)
            if val is not None:
                emissions[pollutant] = float(val)
            else:
                emissions[pollutant] = type_defaults.get(pollutant, 0.0)

        # 굴뚝 높이
        stack_height = parameters.get("stack_height")
        if stack_height is not None:
            H = float(stack_height)
        else:
            H = DEFAULT_STACK_HEIGHT.get(project_type, 20.0)

        # 풍속
        wind_speed = parameters.get("wind_speed")
        if wind_speed is not None:
            u = float(wind_speed)
        else:
            u = DEFAULT_WIND_SPEED

        # 대기안정도 등급
        stability = parameters.get("stability_class", "D").upper()
        if stability not in PG_COEFFICIENTS:
            stability = "D"

        # 예측 실행
        predictions: list[PredictionItem] = []
        for pollutant in TARGET_POLLUTANTS:
            Q = emissions.get(pollutant, 0.0)
            if Q <= 0:
                continue

            info = POLLUTANT_INFO[pollutant]
            bg_conc = bg.get(pollutant, 0.0)

            for dist in PREDICTION_DISTANCES:
                predicted = gaussian_plume_ground_concentration(
                    Q=Q, u=u, H=H, x_m=dist, stability_class=stability,
                )
                total = bg_conc + predicted
                standard_val = info["standard"]

                predictions.append(PredictionItem(
                    label=_format_distance(dist),
                    distance_m=float(dist),
                    pollutant=pollutant,
                    predicted_concentration=round(predicted, 4),
                    background_concentration=round(bg_conc, 4),
                    total_concentration=round(total, 4),
                    unit=info["unit"],
                    standard_value=standard_val,
                    exceeds_standard=total > standard_val,
                ))

        # 요약 생성
        summary = self._generate_summary(predictions, stability, H, u)

        # 전제 조건 및 한계
        assumptions = [
            f"대기안정도 등급: {stability} ({STABILITY_CLASS_NAMES.get(stability, '')})",
            f"유효 굴뚝 높이: {H}m",
            f"평균 풍속: {u} m/s",
            "지형 효과를 고려하지 않은 평탄 지형 가정",
            "풍향은 단일 방향(풍하 중심선) 가정",
            "정상상태(steady-state) 배출 가정",
        ]

        limitations = [
            "가우시안 플룸 모델은 평탄 지형, 균일 기상 조건에서 유효한 간이 모델임",
            "복잡 지형, 해안, 도심 협곡 등에서는 정밀 모델(AERMOD, CALPUFF) 적용이 필요함",
            "화학 반응, 침착, 세정 효과 미반영",
            "풍향 변동에 따른 확산 효과 미반영",
            "배출량은 추정값이며, 실제 사업 설계에 따라 변동 가능",
        ]

        # 입력 파라미터 기록
        input_params = {
            "project_type": project_type,
            "emissions": emissions,
            "stack_height": H,
            "wind_speed": u,
            "stability_class": stability,
            "background_data": bg,
            "distances_m": PREDICTION_DISTANCES,
        }

        return PredictionResult(
            section_key="air_quality",
            model_name="gaussian_plume",
            input_parameters=input_params,
            predictions=predictions,
            summary=summary,
            assumptions=assumptions,
            limitations=limitations,
        )

    def _generate_summary(
        self,
        predictions: list[PredictionItem],
        stability: str,
        stack_height: float,
        wind_speed: float,
    ) -> str:
        """예측 결과 요약 텍스트를 생성한다."""
        if not predictions:
            return "예측 대상 오염물질이 없습니다."

        lines: list[str] = []
        lines.append(
            f"가우시안 플룸 모델(대기안정도 {stability}등급, "
            f"굴뚝높이 {stack_height}m, 풍속 {wind_speed}m/s)에 의한 "
            f"대기질 영향 예측 결과는 다음과 같다."
        )

        # 오염물질별 최대 농도 및 기준 초과 여부
        exceeded: list[str] = []
        for pollutant in TARGET_POLLUTANTS:
            items = [p for p in predictions if p.pollutant == pollutant]
            if not items:
                continue

            # 최대 합산 농도 지점
            max_item = max(items, key=lambda x: x.total_concentration)
            lines.append(
                f"{pollutant}: 최대 영향 지점({max_item.label}) 합산 농도 "
                f"{max_item.total_concentration:.2f} {max_item.unit} "
                f"(배경 {max_item.background_concentration:.2f} + "
                f"기여 {max_item.predicted_concentration:.2f})"
            )

            if max_item.exceeds_standard:
                exceeded.append(
                    f"{pollutant}({max_item.label}: "
                    f"{max_item.total_concentration:.2f} > "
                    f"{max_item.standard_value:.2f} {max_item.unit})"
                )

        if exceeded:
            lines.append(f"환경기준 초과 항목: {', '.join(exceeded)}. 저감대책 검토가 필요하다.")
        else:
            lines.append("모든 오염물질에 대해 환경기준 이내로 예측되었다.")

        return "\n".join(lines)
