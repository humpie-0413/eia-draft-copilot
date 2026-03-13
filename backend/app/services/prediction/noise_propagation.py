"""소음 전파 예측 모델.

점음원(건설장비, 공장 등) 및 선음원(도로)의 거리감쇠 모델로
수음점에서의 소음도를 예측한다.

참조:
- ISO 9613-2 "Acoustics — Attenuation of sound during propagation outdoors"
- Maekawa, Z. (1968) "Noise reduction by screens"
- 환경부 「소음·진동 영향 예측기법 가이드라인」
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
# 사업유형별 기본값
# ────────────────────────────────────────────

DEFAULT_SOURCE_PARAMS: dict[str, dict] = {
    "power_plant": {"source_type": "point", "sound_power_level": 95.0},
    "road":        {"source_type": "line",  "sound_power_level": 75.0},
    "housing":     {"source_type": "point", "sound_power_level": 90.0},
    "industrial":  {"source_type": "point", "sound_power_level": 100.0},
}

# 기타 사업유형은 housing과 동일
for _ptype in ("railway", "airport", "port", "dam", "reclamation", "other"):
    DEFAULT_SOURCE_PARAMS[_ptype] = {"source_type": "point", "sound_power_level": 90.0}

# 예측 대상 거리 (m)
PREDICTION_DISTANCES = [10, 20, 50, 100, 200, 500]

# 대기 흡수 계수 (dB/m) — 1kHz 대역, 15°C, 70%RH 근사
ATMOSPHERIC_ABSORPTION_COEFF = 0.005

# 환경기준 (환경정책기본법 시행령 별표 제1호, 일반지역 "나" 기준)
NOISE_STANDARDS: dict[str, float] = {
    "주간": 55.0,   # dB(A), 06~22시
    "야간": 45.0,   # dB(A), 22~06시
}


# ────────────────────────────────────────────
# 소음 감쇠 계산 함수
# ────────────────────────────────────────────

def point_source_attenuation(
    Lw: float,
    r: float,
    ground_reflection: bool = True,
    atmospheric_absorption: bool = True,
) -> float:
    """점음원 거리감쇠를 계산한다.

    공식: L(r) = Lw - 20·log10(r) - 11
    (자유음장 점음원, 구면파 확산)

    Args:
        Lw: 음향파워레벨 (dB)
        r: 음원~수음점 거리 (m)
        ground_reflection: 지면 반사 보정 (+3dB)
        atmospheric_absorption: 대기 흡수 보정 적용 여부

    Returns:
        수음점 소음도 (dB(A))
    """
    if r <= 0 or Lw <= 0:
        return 0.0

    level = Lw - 20.0 * math.log10(r) - 11.0

    if ground_reflection:
        level += 3.0

    if atmospheric_absorption:
        level -= ATMOSPHERIC_ABSORPTION_COEFF * r

    return max(level, 0.0)


def line_source_attenuation(
    Lw_per_m: float,
    r: float,
    ground_reflection: bool = True,
    atmospheric_absorption: bool = True,
) -> float:
    """선음원(도로) 거리감쇠를 계산한다.

    공식: L(r) = Lw/m - 10·log10(r) - 8
    (무한 길이 비간섭 선음원, 원통파 확산)

    Args:
        Lw_per_m: 단위길이당 음향파워레벨 (dB/m)
        r: 도로~수음점 거리 (m)
        ground_reflection: 지면 반사 보정 (+3dB)
        atmospheric_absorption: 대기 흡수 보정 적용 여부

    Returns:
        수음점 소음도 (dB(A))
    """
    if r <= 0 or Lw_per_m <= 0:
        return 0.0

    level = Lw_per_m - 10.0 * math.log10(r) - 8.0

    if ground_reflection:
        level += 3.0

    if atmospheric_absorption:
        level -= ATMOSPHERIC_ABSORPTION_COEFF * r

    return max(level, 0.0)


def maekawa_barrier_attenuation(
    barrier_height: float,
    source_height: float,
    receiver_height: float,
    distance: float,
) -> float:
    """Maekawa 차음벽 회절 감쇠량을 계산한다.

    프레넬 수 N을 기반으로 회절 감쇠를 산출한다.
    ΔL = 10·log10(3 + 20N)  (N > 0)

    Args:
        barrier_height: 차음벽 높이 (m)
        source_height: 음원 높이 (m, 점음원의 경우 지면 위 높이)
        receiver_height: 수음점 높이 (m)
        distance: 음원~수음점 수평 거리 (m)

    Returns:
        감쇠량 (dB, 양수). 차음벽이 없거나 효과 없으면 0.
    """
    if barrier_height <= 0 or distance <= 0:
        return 0.0

    # 차음벽이 음원과 수음점 사이 중앙에 있다고 가정
    d_source = distance / 2.0   # 음원~차음벽 수평 거리
    d_receiver = distance / 2.0  # 차음벽~수음점 수평 거리

    # 차음벽 유효 높이 (음원-수음점 직선 위 높이)
    # 직선 경로 높이 = 중간지점에서 (source_height + receiver_height) / 2
    line_height_at_barrier = (source_height + receiver_height) / 2.0
    effective_height = barrier_height - line_height_at_barrier

    if effective_height <= 0:
        # 차음벽이 직선 경로보다 낮으면 효과 없음
        return 0.0

    # 경로차 계산: δ = √(d_s² + (h_b - h_s)²) + √(d_r² + (h_b - h_r)²) - √(d² + (h_s - h_r)²)
    path_over = (
        math.sqrt(d_source ** 2 + (barrier_height - source_height) ** 2)
        + math.sqrt(d_receiver ** 2 + (barrier_height - receiver_height) ** 2)
    )
    path_direct = math.sqrt(distance ** 2 + (source_height - receiver_height) ** 2)
    delta = path_over - path_direct

    if delta <= 0:
        return 0.0

    # 프레넬 수: N = 2δ/λ (λ ≈ 0.34m, 1kHz 기준)
    wavelength = 0.34  # 1kHz
    N = 2.0 * delta / wavelength

    if N <= 0:
        return 0.0

    # Maekawa 공식: ΔL = 10·log10(3 + 20N)
    attenuation = 10.0 * math.log10(3.0 + 20.0 * N)

    # 최대 감쇠 제한 (실무적으로 25dB 이상은 어려움)
    return min(attenuation, 25.0)


def energy_sum_db(L1: float, L2: float) -> float:
    """두 소음도의 에너지 합산을 계산한다.

    L_total = 10·log10(10^(L1/10) + 10^(L2/10))

    Args:
        L1: 첫 번째 소음도 (dB)
        L2: 두 번째 소음도 (dB)

    Returns:
        합산 소음도 (dB)
    """
    if L1 <= 0 and L2 <= 0:
        return 0.0
    if L1 <= 0:
        return L2
    if L2 <= 0:
        return L1

    return 10.0 * math.log10(10.0 ** (L1 / 10.0) + 10.0 ** (L2 / 10.0))


def _format_distance(distance_m: float) -> str:
    """거리를 사람이 읽기 쉬운 형태로 변환한다."""
    if distance_m >= 1000:
        km = distance_m / 1000
        return f"{km:g}km"
    return f"{distance_m:g}m"


# ────────────────────────────────────────────
# 소음 전파 모델 클래스
# ────────────────────────────────────────────

class NoisePropagationModel(BasePredictionModel):
    """소음 전파 예측 모델.

    점음원/선음원의 거리감쇠, 차음벽 효과, 에너지 합산을 통해
    수음점에서의 소음도를 예측한다.
    """

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name="noise_propagation",
            display_name="소음 전파 감쇠 모델",
            description=(
                "점음원(건설장비, 공장) 및 선음원(도로)의 거리감쇠 모델. "
                "지면 반사, 대기 흡수, Maekawa 차음벽 회절 감쇠를 반영하며, "
                "기존 소음 현황과 에너지 합산하여 사업 후 예상 소음도를 산출한다."
            ),
            applicable_sections=["noise_vibration"],
        )

    def get_required_inputs(self) -> list[InputParameter]:
        return [
            InputParameter(
                name="project_type",
                display_name="사업 유형",
                unit="",
                default="other",
                required=False,
                description="사업유형별 기본 음원 레벨 적용 (power_plant, road, housing, industrial 등)",
            ),
            InputParameter(
                name="source_type",
                display_name="음원 유형",
                unit="",
                default="point",
                required=False,
                description="point(점음원) 또는 line(선음원/도로)",
            ),
            InputParameter(
                name="sound_power_level",
                display_name="음향파워레벨 (Lw)",
                unit="dB",
                default=None,
                required=False,
                description="음원 레벨 (dB). 미입력 시 사업유형별 기본값 적용",
            ),
            InputParameter(
                name="barrier_height",
                display_name="차음벽 높이",
                unit="m",
                default=0.0,
                required=False,
                description="차음벽 높이 (m). 0이면 차음벽 없음",
            ),
            InputParameter(
                name="receiver_height",
                display_name="수음점 높이",
                unit="m",
                default=1.2,
                required=False,
                description="수음점 높이 (m). 기본값 1.2m (지면 위 귀 높이)",
            ),
            InputParameter(
                name="source_height",
                display_name="음원 높이",
                unit="m",
                default=1.0,
                required=False,
                description="음원 높이 (m). 기본값 1.0m",
            ),
        ]

    def predict(
        self,
        parameters: dict,
        background_data: dict[str, float] | None = None,
    ) -> PredictionResult:
        """소음 전파 예측을 실행한다.

        Args:
            parameters: 입력 파라미터
            background_data: 배경 소음 데이터
                {"소음_Leq_주간": 52.0, "소음_Leq_야간": 40.0} 형태
        """
        bg = background_data or {}
        project_type = parameters.get("project_type", "other")

        # 사업유형별 기본값
        type_defaults = DEFAULT_SOURCE_PARAMS.get(
            project_type, DEFAULT_SOURCE_PARAMS["other"]
        )

        # 음원 유형
        source_type = parameters.get("source_type")
        if source_type is None:
            source_type = type_defaults["source_type"]

        # 음향파워레벨
        Lw = parameters.get("sound_power_level")
        if Lw is not None:
            Lw = float(Lw)
        else:
            Lw = type_defaults["sound_power_level"]

        # 차음벽 / 수음점 / 음원 높이
        barrier_height = float(parameters.get("barrier_height", 0.0))
        receiver_height = float(parameters.get("receiver_height", 1.2))
        source_height = float(parameters.get("source_height", 1.0))

        # 배경 소음
        bg_day = bg.get("소음_Leq_주간", 0.0)
        bg_night = bg.get("소음_Leq_야간", 0.0)

        # 예측 실행
        predictions: list[PredictionItem] = []

        for dist in PREDICTION_DISTANCES:
            # 거리 감쇠 계산
            if source_type == "line":
                predicted_level = line_source_attenuation(Lw, dist)
            else:
                predicted_level = point_source_attenuation(Lw, dist)

            # 차음벽 감쇠 적용
            if barrier_height > 0:
                barrier_atten = maekawa_barrier_attenuation(
                    barrier_height, source_height, receiver_height, dist,
                )
                predicted_level = max(predicted_level - barrier_atten, 0.0)

            # 주간: 에너지 합산 + 기준 비교
            total_day = energy_sum_db(bg_day, predicted_level)
            std_day = NOISE_STANDARDS["주간"]

            predictions.append(PredictionItem(
                label=_format_distance(dist),
                distance_m=float(dist),
                pollutant="소음_Leq_주간",
                predicted_concentration=round(predicted_level, 1),
                background_concentration=round(bg_day, 1),
                total_concentration=round(total_day, 1),
                unit="dB(A)",
                standard_value=std_day,
                exceeds_standard=total_day > std_day,
            ))

            # 야간: 에너지 합산 + 기준 비교
            total_night = energy_sum_db(bg_night, predicted_level)
            std_night = NOISE_STANDARDS["야간"]

            predictions.append(PredictionItem(
                label=_format_distance(dist),
                distance_m=float(dist),
                pollutant="소음_Leq_야간",
                predicted_concentration=round(predicted_level, 1),
                background_concentration=round(bg_night, 1),
                total_concentration=round(total_night, 1),
                unit="dB(A)",
                standard_value=std_night,
                exceeds_standard=total_night > std_night,
            ))

        # 요약
        summary = self._generate_summary(predictions, source_type, Lw, barrier_height)

        # 전제 조건 / 한계
        source_desc = "선음원(도로)" if source_type == "line" else "점음원"
        assumptions = [
            f"음원 유형: {source_desc}, 음향파워레벨: {Lw} dB",
            f"수음점 높이: {receiver_height}m, 음원 높이: {source_height}m",
            "지면 반사 보정(+3dB) 적용 (반사면 위 전파)",
            f"대기 흡수 계수: {ATMOSPHERIC_ABSORPTION_COEFF} dB/m (1kHz 기준)",
        ]
        if barrier_height > 0:
            assumptions.append(f"차음벽 높이: {barrier_height}m (음원-수음점 중간 위치 가정)")
        else:
            assumptions.append("차음벽 없음")

        limitations = [
            "점음원/선음원 간이 감쇠 모델로 평탄 지형, 균일 조건 가정",
            "주파수별 감쇠 특성 미반영 (A가중 근사)",
            "건물 반사, 회절 등 도심 환경 효과 미반영",
            "기상 조건(역전층, 바람) 변화에 따른 전파 특성 미반영",
            "정밀 예측에는 소음지도 모델(SoundPLAN 등) 적용이 필요함",
        ]

        input_params = {
            "project_type": project_type,
            "source_type": source_type,
            "sound_power_level": Lw,
            "barrier_height": barrier_height,
            "receiver_height": receiver_height,
            "source_height": source_height,
            "background_data": bg,
            "distances_m": PREDICTION_DISTANCES,
        }

        return PredictionResult(
            section_key="noise_vibration",
            model_name="noise_propagation",
            input_parameters=input_params,
            predictions=predictions,
            summary=summary,
            assumptions=assumptions,
            limitations=limitations,
        )

    def _generate_summary(
        self,
        predictions: list[PredictionItem],
        source_type: str,
        Lw: float,
        barrier_height: float,
    ) -> str:
        """예측 결과 요약 텍스트를 생성한다."""
        if not predictions:
            return "예측 대상이 없습니다."

        lines: list[str] = []
        source_desc = "선음원(도로)" if source_type == "line" else "점음원"
        barrier_desc = f", 차음벽 {barrier_height}m" if barrier_height > 0 else ""

        lines.append(
            f"소음 전파 감쇠 모델({source_desc}, Lw={Lw}dB{barrier_desc})에 의한 "
            f"소음 영향 예측 결과는 다음과 같다."
        )

        # 주간/야간별 최대 합산 소음도
        exceeded: list[str] = []
        for period_label, period_key in [("주간", "소음_Leq_주간"), ("야간", "소음_Leq_야간")]:
            items = [p for p in predictions if p.pollutant == period_key]
            if not items:
                continue

            # 가장 가까운 거리(최대 소음) 지점
            max_item = max(items, key=lambda x: x.total_concentration)
            # 가장 먼 거리 지점
            min_item = min(items, key=lambda x: x.total_concentration)

            lines.append(
                f"{period_label}: 최근접({max_item.label}) {max_item.total_concentration:.1f} dB(A), "
                f"최원거리({min_item.label}) {min_item.total_concentration:.1f} dB(A)"
            )

            exceeded_items = [p for p in items if p.exceeds_standard]
            if exceeded_items:
                dists = ", ".join(p.label for p in exceeded_items)
                exceeded.append(f"{period_label}({dists})")

        if exceeded:
            lines.append(f"환경기준 초과 구간: {', '.join(exceeded)}. 저감대책 검토가 필요하다.")
        else:
            lines.append("모든 예측 지점에서 소음환경기준 이내로 예측되었다.")

        return "\n".join(lines)
