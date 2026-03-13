"""수질 혼합 예측 모델 — 완전혼합 희석.

사업장 방류수가 하천에 유입될 때의 혼합 후 수질 농도를 예측한다.
완전혼합(complete mixing) 모델을 적용한다.

참조:
- Fischer, H.B. et al. (1979) "Mixing in Inland and Coastal Waters"
- 환경부 「수질영향 예측기법 가이드라인」
- 물환경보전법 시행규칙 별표 13 (방류수 수질기준)
"""

from __future__ import annotations

from app.services.prediction.base import (
    BasePredictionModel,
    InputParameter,
    ModelInfo,
    PredictionItem,
    PredictionResult,
)


# ────────────────────────────────────────────
# 방류수 수질기준 (물환경보전법 시행규칙 별표 13)
# ────────────────────────────────────────────

DISCHARGE_STANDARDS: dict[str, float] = {
    "BOD": 30.0,    # mg/L
    "COD": 40.0,    # mg/L
    "SS": 30.0,     # mg/L
    "T-N": 60.0,    # mg/L
    "T-P": 8.0,     # mg/L
}

# 대상 오염물질
TARGET_POLLUTANTS = list(DISCHARGE_STANDARDS.keys())

# 오염물질별 단위 및 하천 환경기준 (III등급 '보통' 기준)
POLLUTANT_INFO: dict[str, dict] = {
    "BOD": {"unit": "mg/L", "standard": 5.0, "description": "생물화학적산소요구량"},
    "COD": {"unit": "mg/L", "standard": 7.0, "description": "화학적산소요구량"},
    "SS":  {"unit": "mg/L", "standard": 25.0, "description": "부유물질"},
    "T-N": {"unit": "mg/L", "standard": None, "description": "총질소"},  # 등급 기준 없음
    "T-P": {"unit": "mg/L", "standard": 0.2, "description": "총인"},
}

# ────────────────────────────────────────────
# 사업유형별 기본 방류량 (m³/s)
# ────────────────────────────────────────────

DEFAULT_DISCHARGE_FLOW: dict[str, float] = {
    "power_plant": 0.01,
    "industrial": 0.1,
    "housing": 0.05,
}

# 기타 사업유형
for _ptype in ("road", "railway", "airport", "port", "dam", "reclamation", "other"):
    DEFAULT_DISCHARGE_FLOW[_ptype] = 0.02

# 기본 하천 유량 (m³/s) — 중소 하천 갈수기 유량 근사
DEFAULT_RIVER_FLOW = 1.0


# ────────────────────────────────────────────
# 혼합 계산 함수
# ────────────────────────────────────────────

def complete_mixing_concentration(
    Q_river: float,
    C_river: float,
    Q_discharge: float,
    C_discharge: float,
) -> float:
    """완전혼합 희석 모델로 혼합 후 농도를 계산한다.

    공식: C_mix = (Q_river · C_river + Q_discharge · C_discharge) / (Q_river + Q_discharge)

    Args:
        Q_river: 하천 유량 (m³/s)
        C_river: 하천 기존 농도 (mg/L)
        Q_discharge: 방류량 (m³/s)
        C_discharge: 방류수 농도 (mg/L)

    Returns:
        혼합 후 농도 (mg/L)
    """
    total_flow = Q_river + Q_discharge
    if total_flow <= 0:
        return 0.0

    return (Q_river * C_river + Q_discharge * C_discharge) / total_flow


class WaterMixingModel(BasePredictionModel):
    """수질 완전혼합 예측 모델.

    사업장 방류수의 하천 유입 시 완전혼합을 가정하여
    혼합 후 수질 농도를 예측한다.
    """

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name="water_mixing",
            display_name="완전혼합 수질 희석 모델",
            description=(
                "사업장 방류수가 하천에 유입될 때 완전혼합을 가정한 희석 모델. "
                "BOD, COD, SS, T-N, T-P에 대해 혼합 후 농도를 예측하며, "
                "기존 수질 현황과 방류수 수질기준(물환경보전법)을 적용한다."
            ),
            applicable_sections=["water_quality"],
        )

    def get_required_inputs(self) -> list[InputParameter]:
        return [
            InputParameter(
                name="project_type",
                display_name="사업 유형",
                unit="",
                default="other",
                required=False,
                description="사업유형별 기본 방류량 적용 (power_plant, industrial, housing 등)",
            ),
            InputParameter(
                name="river_flow",
                display_name="하천 유량",
                unit="m³/s",
                default=DEFAULT_RIVER_FLOW,
                required=False,
                description="하천 유량. 미입력 시 기본값(1.0 m³/s) 적용",
            ),
            InputParameter(
                name="discharge_flow",
                display_name="방류량",
                unit="m³/s",
                default=None,
                required=False,
                description="방류량. 미입력 시 사업유형별 기본값 적용",
            ),
            InputParameter(
                name="discharge_bod",
                display_name="방류수 BOD",
                unit="mg/L",
                default=DISCHARGE_STANDARDS["BOD"],
                required=False,
                description="방류수 BOD 농도. 기본값: 방류수 수질기준 30 mg/L",
            ),
            InputParameter(
                name="discharge_cod",
                display_name="방류수 COD",
                unit="mg/L",
                default=DISCHARGE_STANDARDS["COD"],
                required=False,
                description="방류수 COD 농도. 기본값: 방류수 수질기준 40 mg/L",
            ),
            InputParameter(
                name="discharge_ss",
                display_name="방류수 SS",
                unit="mg/L",
                default=DISCHARGE_STANDARDS["SS"],
                required=False,
                description="방류수 SS 농도. 기본값: 방류수 수질기준 30 mg/L",
            ),
            InputParameter(
                name="discharge_tn",
                display_name="방류수 T-N",
                unit="mg/L",
                default=DISCHARGE_STANDARDS["T-N"],
                required=False,
                description="방류수 T-N 농도. 기본값: 방류수 수질기준 60 mg/L",
            ),
            InputParameter(
                name="discharge_tp",
                display_name="방류수 T-P",
                unit="mg/L",
                default=DISCHARGE_STANDARDS["T-P"],
                required=False,
                description="방류수 T-P 농도. 기본값: 방류수 수질기준 8 mg/L",
            ),
        ]

    def predict(
        self,
        parameters: dict,
        background_data: dict[str, float] | None = None,
    ) -> PredictionResult:
        """수질 혼합 예측을 실행한다.

        Args:
            parameters: 입력 파라미터
            background_data: 기존 수질 현황
                {"BOD": 2.5, "COD": 4.0, "SS": 10.0, "T-N": 3.0, "T-P": 0.1} 형태
        """
        bg = background_data or {}
        project_type = parameters.get("project_type", "other")

        # 하천 유량
        river_flow = parameters.get("river_flow")
        if river_flow is not None:
            Q_river = float(river_flow)
        else:
            Q_river = DEFAULT_RIVER_FLOW

        # 방류량
        discharge_flow = parameters.get("discharge_flow")
        if discharge_flow is not None:
            Q_discharge = float(discharge_flow)
        else:
            Q_discharge = DEFAULT_DISCHARGE_FLOW.get(
                project_type, DEFAULT_DISCHARGE_FLOW["other"]
            )

        # 방류수 농도 (사용자 입력 우선, 없으면 방류수 수질기준)
        discharge_conc: dict[str, float] = {}
        param_keys = {
            "BOD": "discharge_bod",
            "COD": "discharge_cod",
            "SS": "discharge_ss",
            "T-N": "discharge_tn",
            "T-P": "discharge_tp",
        }
        for pollutant, param_key in param_keys.items():
            val = parameters.get(param_key)
            if val is not None:
                discharge_conc[pollutant] = float(val)
            else:
                discharge_conc[pollutant] = DISCHARGE_STANDARDS[pollutant]

        # 혼합 계산
        predictions: list[PredictionItem] = []

        for pollutant in TARGET_POLLUTANTS:
            info = POLLUTANT_INFO[pollutant]
            C_river = bg.get(pollutant, 0.0)
            C_discharge = discharge_conc[pollutant]

            C_mix = complete_mixing_concentration(
                Q_river, C_river, Q_discharge, C_discharge,
            )

            standard_val = info["standard"]
            exceeds = False
            if standard_val is not None:
                exceeds = C_mix > standard_val

            predictions.append(PredictionItem(
                label="혼합 후",
                distance_m=0.0,  # 혼합 모델은 거리 개념 없음
                pollutant=pollutant,
                predicted_concentration=round(C_discharge, 4),
                background_concentration=round(C_river, 4),
                total_concentration=round(C_mix, 4),
                unit=info["unit"],
                standard_value=standard_val,
                exceeds_standard=exceeds,
            ))

        # 요약
        summary = self._generate_summary(
            predictions, Q_river, Q_discharge, project_type,
        )

        # 전제 조건 / 한계
        assumptions = [
            f"하천 유량: {Q_river} m³/s",
            f"방류량: {Q_discharge} m³/s (유량비 {Q_discharge/Q_river*100:.1f}%)"
            if Q_river > 0 else f"방류량: {Q_discharge} m³/s",
            "완전혼합(complete mixing) 가정",
            "방류수 농도는 물환경보전법 시행규칙 별표 13 방류수 수질기준 적용",
            "하천 기존 수질은 수질측정망 평균값 사용",
        ]

        limitations = [
            "완전혼합 모델은 방류구 직하류에서의 최대 농도를 과소평가할 수 있음",
            "근역(near-field) 혼합 과정 및 농도 분포 미반영",
            "수온, 유속 변화에 따른 반응속도 미반영",
            "갈수기/풍수기 유량 변동 미반영 (대표 유량 사용)",
            "정밀 예측에는 수리·수질 모델(QUAL2E, WASP 등) 적용이 필요함",
        ]

        input_params = {
            "project_type": project_type,
            "river_flow": Q_river,
            "discharge_flow": Q_discharge,
            "discharge_concentrations": discharge_conc,
            "background_data": bg,
        }

        return PredictionResult(
            section_key="water_quality",
            model_name="water_mixing",
            input_parameters=input_params,
            predictions=predictions,
            summary=summary,
            assumptions=assumptions,
            limitations=limitations,
        )

    def _generate_summary(
        self,
        predictions: list[PredictionItem],
        Q_river: float,
        Q_discharge: float,
        project_type: str,
    ) -> str:
        """예측 결과 요약 텍스트를 생성한다."""
        if not predictions:
            return "예측 대상 오염물질이 없습니다."

        lines: list[str] = []
        ratio = Q_discharge / Q_river * 100 if Q_river > 0 else 0
        lines.append(
            f"완전혼합 희석 모델(하천유량 {Q_river} m³/s, "
            f"방류량 {Q_discharge} m³/s, 유량비 {ratio:.1f}%)에 의한 "
            f"수질 영향 예측 결과는 다음과 같다."
        )

        exceeded: list[str] = []
        for p in predictions:
            std_str = f", 기준 {p.standard_value}" if p.standard_value is not None else ""
            lines.append(
                f"{p.pollutant}: 혼합 후 {p.total_concentration:.2f} {p.unit} "
                f"(하천 {p.background_concentration:.2f} + "
                f"방류 {p.predicted_concentration:.2f}{std_str})"
            )
            if p.exceeds_standard:
                exceeded.append(
                    f"{p.pollutant}({p.total_concentration:.2f} > "
                    f"{p.standard_value} {p.unit})"
                )

        if exceeded:
            lines.append(
                f"환경기준 초과 항목: {', '.join(exceeded)}. 저감대책 검토가 필요하다."
            )
        else:
            lines.append("모든 오염물질에 대해 환경기준 이내로 예측되었다.")

        return "\n".join(lines)
