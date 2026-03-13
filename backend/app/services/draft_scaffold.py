"""초안 뼈대 생성 서비스.

evidence 데이터를 섹션별로 분류하여 초안 뼈대 구조를 생성한다.
핵심 원칙: unsupported claim 금지 — LLM 자유 작문이 아닌 evidence 기반
근거 나열 방식으로만 텍스트를 배치한다.

Post-3 개편: 서술문 → 통계 요약 테이블 → 환경기준 비교 테이블 → 상세 데이터 샘플(최대 5건)
Pred-3 추가: 예측 모델 실행 결과 및 예측 서술문 포함
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import draft_narrative as draft_narrative_crud
from app.models.evidence import Evidence
from app.models.project import Project
from app.services.narrative_generator import generate_narrative, generate_prediction_narrative
from app.services.prediction.base import PredictionResult
from app.services.prediction.registry import get_default_model_for_section
from app.services.section_planner import (
    EIA_SECTIONS,
    SectionDefinition,
    calculate_section_status,
    get_section_definition,
)
from app.services.standard_checker import (
    CheckStatus,
    IndicatorCheckResult,
    SectionCheckResult,
    check_section_standards,
)
from app.services.statistics import (
    IndicatorStats,
    SectionStats,
    calculate_section_statistics,
)

# 상세 데이터 부록에 표시할 최대 샘플 건수
MAX_DETAIL_SAMPLES = 5


@dataclass
class EvidenceEntry:
    """초안 뼈대에 배치되는 개별 근거 항목."""

    evidence_id: str
    indicator: str
    value: str
    numeric_value: float | None
    unit: str | None
    observed_at: str | None      # ISO 문자열
    data_source_id: str | None
    metadata_json: dict | None


@dataclass
class ScaffoldSection:
    """초안 뼈대의 섹션 단위."""

    section_key: str
    title: str
    description: str
    order: int
    evidence_entries: list[EvidenceEntry] = field(default_factory=list)
    summary_text: str = ""          # evidence 기반 자동 생성 요약문
    narrative: str = ""             # Post-3: 서술문 템플릿 엔진 결과
    state: str = "empty"            # 섹션 상태 (output-contracts.md 스펙)
    missing_indicators: list[str] = field(default_factory=list)  # 누락된 필수 지표
    # Pred-3: 예측 모델 실행 결과 및 예측 서술문
    prediction_result: PredictionResult | None = None
    prediction_narrative: str = ""


@dataclass
class DraftScaffold:
    """초안 뼈대 전체 구조."""

    project_id: str
    generated_at: str               # ISO 문자열
    sections: list[ScaffoldSection] = field(default_factory=list)
    total_evidence_count: int = 0


def _short_legal_ref(legal_basis: str) -> str:
    """법적 근거를 테이블 열에 적합한 간략 형태로 변환한다."""
    if not legal_basis:
        return "-"
    if "환경정책기본법" in legal_basis:
        return "환경정책기본법 별표1"
    if "토양환경보전법" in legal_basis:
        return "토양환경보전법 별표3"
    return legal_basis[:20]


def _format_period(start: str | None, end: str | None) -> str:
    """관측 기간 문자열을 생성한다."""
    if start and end:
        s = start[:10]
        e = end[:10]
        return f"{s}~{e}" if s != e else s
    if start:
        return start[:10]
    if end:
        return end[:10]
    return "-"


def _format_stats_summary(
    section_def: SectionDefinition,
    entries: list[EvidenceEntry],
    indicator_stats: list[IndicatorStats],
    check_results: list[IndicatorCheckResult] | None = None,
) -> str:
    """통계 요약 테이블 + 환경기준 비교 테이블 + 상세 데이터 샘플 텍스트를 생성한다.

    Post-3 개편: 서술문 제거 (narrative 필드로 분리), 구조 정리
    """
    if not entries:
        return ""

    lines: list[str] = []

    # 환경기준 비교 결과를 지표명 기준 딕셔너리로 구성
    check_map: dict[str, IndicatorCheckResult] = {}
    if check_results:
        for cr in check_results:
            check_map[cr.indicator] = cr
    has_standards = bool(check_map)

    # ── 1. 측정 현황 요약 (통계 테이블) ──
    stats_with_data = [s for s in indicator_stats if s.count > 0]
    if stats_with_data:
        lines.append(f"[측정 현황 요약] ({len(entries)}건 기준)")
        lines.append("")

        if has_standards:
            lines.append("지표명 | 평균 | 최대 | 최소 | 건수 | 환경기준 | 판정 | 법적 근거 | 기간")
            lines.append("--- | --- | --- | --- | --- | --- | --- | --- | ---")
        else:
            lines.append("지표명 | 평균 | 최대 | 최소 | 건수 | 기간")
            lines.append("--- | --- | --- | --- | --- | ---")

        for s in stats_with_data:
            unit_suffix = f" {s.unit}" if s.unit else ""
            mean_str = f"{s.mean}{unit_suffix}" if s.mean is not None else "-"
            max_str = f"{s.max_value}{unit_suffix}" if s.max_value is not None else "-"
            min_str = f"{s.min_value}{unit_suffix}" if s.min_value is not None else "-"
            period = _format_period(s.period_start, s.period_end)

            if has_standards:
                cr = check_map.get(s.indicator)
                if cr and cr.standard_value is not None:
                    std_unit = cr.standard_unit or ""
                    std_str = f"{cr.standard_value:.4g} {std_unit}".strip()
                    status_str = "적합" if cr.status == CheckStatus.PASS else (
                        "초과" if cr.status == CheckStatus.FAIL else "-"
                    )
                    legal_short = _short_legal_ref(cr.legal_basis)
                else:
                    std_str = "-"
                    status_str = "-"
                    legal_short = "-"
                lines.append(
                    f"{s.indicator} | {mean_str} | {max_str} | {min_str} | "
                    f"{s.count} | {std_str} | {status_str} | {legal_short} | {period}"
                )
            else:
                lines.append(
                    f"{s.indicator} | {mean_str} | {max_str} | {min_str} | {s.count} | {period}"
                )
        lines.append("")

    # 비수치 데이터는 별도 나열
    numeric_indicators = {s.indicator for s in stats_with_data}
    non_numeric_entries = [e for e in entries if e.indicator not in numeric_indicators]
    if non_numeric_entries:
        non_numeric_groups: dict[str, list[EvidenceEntry]] = {}
        for entry in non_numeric_entries:
            non_numeric_groups.setdefault(entry.indicator, []).append(entry)

        lines.append(f"[비수치 데이터] ({len(non_numeric_entries)}건)")
        lines.append("")
        for indicator, group in non_numeric_groups.items():
            lines.append(f"■ {indicator}")
            for entry in group:
                date_part = f" (관측: {entry.observed_at[:10]})" if entry.observed_at else ""
                lines.append(f"  - {entry.value}{date_part}")
            lines.append("")

    # ── 2. 상세 데이터 샘플 (최대 5건) ──
    sample_count = min(len(entries), MAX_DETAIL_SAMPLES)
    lines.append(f"[측정 데이터] (대표 {sample_count}건)")
    lines.append("")

    sample_entries = entries[:MAX_DETAIL_SAMPLES]
    for entry in sample_entries:
        date_part = f" (관측: {entry.observed_at[:10]})" if entry.observed_at else ""
        unit_part = f" {entry.unit}" if entry.unit else ""
        lines.append(f"  - {entry.indicator}: {entry.value}{unit_part}{date_part}")

    if len(entries) > MAX_DETAIL_SAMPLES:
        lines.append(f"  ... 외 {len(entries) - MAX_DETAIL_SAMPLES}건은 별첨 참조")

    return "\n".join(lines)


async def _fetch_section_evidences(
    db: AsyncSession,
    project_id: uuid.UUID,
    category: str,
) -> list[Evidence]:
    """섹션에 해당하는 본 평가 evidence를 조회한다."""
    result = await db.execute(
        select(Evidence)
        .where(
            (Evidence.project_id == project_id)
            & (Evidence.category == category)
            & (Evidence.screening_only.is_(False))
        )
        .order_by(Evidence.indicator, Evidence.observed_at.desc())
    )
    return list(result.scalars().all())


def _evidence_to_entry(ev: Evidence) -> EvidenceEntry:
    """ORM Evidence 객체를 EvidenceEntry로 변환한다."""
    return EvidenceEntry(
        evidence_id=str(ev.id),
        indicator=ev.indicator,
        value=ev.value,
        numeric_value=ev.numeric_value,
        unit=ev.unit,
        observed_at=ev.observed_at.isoformat() if ev.observed_at else None,
        data_source_id=str(ev.data_source_id) if ev.data_source_id else None,
        metadata_json=ev.metadata_json,
    )


def _extract_background_data(
    section_key: str,
    entries: list[EvidenceEntry],
) -> dict[str, float]:
    """evidence 항목에서 섹션별 배경 농도 데이터를 추출한다.

    지표별 numeric_value 평균값을 계산하여 예측 모델의 background_data로 사용한다.
    """
    # 섹션별 배경 지표 매핑: evidence indicator → 예측 모델 키
    INDICATOR_MAP: dict[str, dict[str, str]] = {
        "air_quality": {
            "PM10_연평균": "PM10",
            "PM2.5_연평균": "PM2.5",
            "NO2_연평균": "NO2",
            "SO2_연평균": "SO2",
            "CO_연평균": "CO",
            "O3_연평균": "O3",
        },
        "noise_vibration": {
            "소음_Leq_주간": "소음_Leq_주간",
            "소음_Leq_야간": "소음_Leq_야간",
        },
        "water_quality": {
            "BOD": "BOD",
            "COD": "COD",
            "SS": "SS",
            "T-N": "T-N",
            "T-P": "T-P",
        },
    }

    indicator_map = INDICATOR_MAP.get(section_key, {})
    if not indicator_map:
        return {}

    # 지표별 numeric_value 수집
    bucket: dict[str, list[float]] = {}
    for entry in entries:
        model_key = indicator_map.get(entry.indicator)
        if model_key and entry.numeric_value is not None:
            bucket.setdefault(model_key, []).append(entry.numeric_value)

    # 평균 계산
    return {key: sum(vals) / len(vals) for key, vals in bucket.items() if vals}


async def generate_section_scaffold(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_key: str,
    project_type: str | None = None,
) -> ScaffoldSection | None:
    """단일 섹션의 초안 뼈대를 생성한다.

    Args:
        db: DB 세션
        project_id: 프로젝트 UUID
        section_key: 섹션 키
        project_type: 사업 유형 (예측 모델 기본값 적용에 사용)
    """
    section_def = get_section_definition(section_key)
    if section_def is None:
        return None

    evidences = await _fetch_section_evidences(
        db, project_id, section_def.evidence_category
    )

    entries = [_evidence_to_entry(ev) for ev in evidences]

    # 통계 계산 (기본 필터 적용)
    section_stats = await calculate_section_statistics(
        db, project_id, section_key
    )
    indicator_stats = section_stats.indicator_stats if section_stats else []

    # 환경기준 비교 (기본 필터 적용)
    section_check = await check_section_standards(db, project_id, section_key)
    check_results = section_check.indicators if section_check else None

    # 서술문 생성: 항상 템플릿 서술문(법적 근거 포함) 생성 후,
    # LLM 보강 서술문이 법적 근거를 포함하는 경우에만 대체 사용
    template_narrative = generate_narrative(section_def, section_stats, section_check)

    saved_narrative = await draft_narrative_crud.get_narrative(
        db, project_id, section_key
    )
    if saved_narrative:
        _LEGAL_KEYWORDS = ("환경정책기본법", "토양환경보전법", "환경영향평가법")
        if any(kw in saved_narrative.narrative_text for kw in _LEGAL_KEYWORDS):
            narrative = saved_narrative.narrative_text
        else:
            # LLM 서술문에 법적 근거가 없으면 템플릿 서술문 사용
            narrative = template_narrative
    else:
        narrative = template_narrative

    # 통계 요약 테이블 + 상세 데이터 샘플
    summary = _format_stats_summary(
        section_def, entries, indicator_stats,
        check_results=check_results,
    )

    # 섹션 상태 조회하여 state, missing_indicators 반영
    section_status = await calculate_section_status(db, project_id, section_key)
    state = section_status.status if section_status else "empty"
    missing = section_status.missing_indicators if section_status else []

    # Pred-3: 예측 모델 실행
    prediction_result: PredictionResult | None = None
    pred_narrative = ""

    model = get_default_model_for_section(section_key)
    if model is not None:
        # evidence에서 배경 농도 데이터 추출
        bg_data = _extract_background_data(section_key, entries)

        # 사업 유형 파라미터 구성 (project_type 없으면 기본값 "other")
        params: dict = {"project_type": project_type or "other"}

        try:
            prediction_result = model.predict(
                parameters=params,
                background_data=bg_data if bg_data else None,
            )
            pred_narrative = generate_prediction_narrative(
                section_key, prediction_result
            )
        except Exception:
            # 예측 실패 시 결과 없이 계속 진행
            prediction_result = None
            pred_narrative = ""

    return ScaffoldSection(
        section_key=section_def.key,
        title=section_def.title,
        description=section_def.description,
        order=section_def.order,
        evidence_entries=entries,
        summary_text=summary,
        narrative=narrative,
        state=state,
        missing_indicators=missing,
        prediction_result=prediction_result,
        prediction_narrative=pred_narrative,
    )


async def generate_draft_scaffold(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> DraftScaffold:
    """프로젝트의 전체 초안 뼈대를 생성한다.

    모든 섹션에 대해 evidence를 수집하고 근거 텍스트를 배치한다.
    Pred-3: project_type을 DB에서 조회하여 각 섹션 예측 모델에 전달한다.
    """
    # project_type 조회 — 예측 모델 기본값 적용에 사용
    project_type: str | None = None
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if project is not None:
        project_type = project.project_type

    sections = []
    total_count = 0

    for section_def in EIA_SECTIONS:
        scaffold = await generate_section_scaffold(
            db, project_id, section_def.key,
            project_type=project_type,
        )
        if scaffold is not None:
            sections.append(scaffold)
            total_count += len(scaffold.evidence_entries)

    return DraftScaffold(
        project_id=str(project_id),
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
        sections=sections,
        total_evidence_count=total_count,
    )
