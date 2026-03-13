"""결정적 QA 규칙 엔진.

섹션별 필수 증거 누락 검사, unsupported claim 검출, 심각도 등급 판정을 수행한다.
규칙은 결정적(deterministic)으로 동작하며 LLM을 사용하지 않는다.

규칙 목록:
- R001: 섹션 증거 없음 (사업유형 기반 동적 심각도)
- R002: 필수 지표 누락
- R003: 충족도 50% 미만
- R004: 근거 없는 완료 상태 (unsupported claim)
- R005: 단일 근거 지표
- R006: 환경기준 초과
- R007: 법적 필수 섹션 누락 (사업유형 기반)
- R008: 법적 필수 지표 누락 (사업유형 기반)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project import get_project
from app.data.regulations.required_items import (
    REQUIRED_BY_TYPE,
    get_required_indicators,
    get_required_sections,
)
from app.services.section_planner import (
    EIA_SECTIONS,
    SectionDefinition,
    calculate_section_status,
    SectionStatus,
)
from app.services.standard_checker import (
    CheckStatus,
    check_section_standards,
)


class Severity(str, Enum):
    """QA 이슈 심각도 등급."""

    CRITICAL = "critical"   # export 차단
    WARNING = "warning"     # 경고 (export 가능)
    INFO = "info"           # 참고 정보


@dataclass
class QaIssue:
    """단일 QA 이슈."""

    rule_id: str                # 규칙 고유 ID
    severity: Severity          # 심각도
    section_key: str | None     # 관련 섹션 (None이면 프로젝트 전체)
    title: str                  # 이슈 제목
    message: str                # 상세 설명
    indicators: list[str] = field(default_factory=list)  # 관련 지표 목록
    legal_basis: str = ""       # 법적 근거 (R007, R008에서 사용)


@dataclass
class QaSummary:
    """QA 결과 요약 통계."""

    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0

    @property
    def total(self) -> int:
        return self.critical_count + self.warning_count + self.info_count


@dataclass
class QaResult:
    """QA 실행 결과."""

    project_id: str
    run_at: str                               # ISO 문자열
    issues: list[QaIssue] = field(default_factory=list)
    summary: QaSummary = field(default_factory=QaSummary)
    export_ready: bool = True                 # critical 이슈가 없으면 True


# ────────────────────────────────────────────
# 핵심 섹션 정의 (사업유형 미설정 시 fallback)
# ────────────────────────────────────────────

_CRITICAL_SECTIONS_FALLBACK = {
    "air_quality", "water_quality", "noise_vibration", "ecology",
}


def _get_critical_sections(project_type: str | None) -> set[str]:
    """사업유형 기반 필수 섹션 집합을 반환한다.

    사업유형이 설정되어 있으면 required_items 데이터를 사용하고,
    미설정이면 기존 하드코딩 fallback을 사용한다.
    """
    if project_type:
        return set(get_required_sections(project_type))
    return set(_CRITICAL_SECTIONS_FALLBACK)


def _get_project_type_name(project_type: str) -> str:
    """사업유형 코드를 한글명으로 변환한다."""
    req = REQUIRED_BY_TYPE.get(project_type)
    if req is not None:
        return req.type_name
    return project_type


# ────────────────────────────────────────────
# 규칙 함수들
# ────────────────────────────────────────────

def _rule_section_empty(
    section_def: SectionDefinition,
    section_status: SectionStatus,
    critical_sections: set[str],
    *,
    legally_required: bool = False,
) -> QaIssue | None:
    """R001: 섹션에 증거가 전혀 없는 경우.

    법적 필수 섹션은 R007에서 별도 처리하므로 건너뛴다.
    """
    if section_status.total_evidence_count > 0:
        return None

    # 법적 필수 섹션은 R007에서 처리
    if legally_required:
        return None

    # 사업유형 기반 동적 심각도 판단
    is_critical = section_def.key in critical_sections
    severity = Severity.CRITICAL if is_critical else Severity.WARNING

    return QaIssue(
        rule_id="R001",
        severity=severity,
        section_key=section_def.key,
        title=f"{section_def.title} 섹션 증거 없음",
        message=f"{section_def.title} 섹션에 대한 증거 데이터가 전혀 수집되지 않았습니다.",
        indicators=section_def.required_indicators,
    )


def _rule_missing_required_indicators(
    section_def: SectionDefinition,
    section_status: SectionStatus,
    critical_sections: set[str],
) -> list[QaIssue]:
    """R002: 필수 지표 누락 검사."""
    issues: list[QaIssue] = []
    if section_status.total_evidence_count == 0:
        # R001/R007에서 이미 처리됨
        return issues

    missing = [
        ind.name
        for ind in section_status.required_indicators
        if not ind.fulfilled
    ]
    if not missing:
        return issues

    # 사업유형 기반 동적 심각도 판단
    is_critical = section_def.key in critical_sections
    severity = Severity.CRITICAL if is_critical else Severity.WARNING

    issues.append(QaIssue(
        rule_id="R002",
        severity=severity,
        section_key=section_def.key,
        title=f"{section_def.title} 필수 지표 누락 ({len(missing)}건)",
        message=(
            f"{section_def.title} 섹션의 필수 지표 중 {len(missing)}건이 "
            f"누락되었습니다: {', '.join(missing)}"
        ),
        indicators=missing,
    ))
    return issues


def _rule_low_coverage(
    section_def: SectionDefinition,
    section_status: SectionStatus,
) -> QaIssue | None:
    """R003: 충족도 50% 미만 경고."""
    if section_status.total_evidence_count == 0:
        return None  # R001에서 처리
    if section_status.coverage_ratio >= 0.5:
        return None

    return QaIssue(
        rule_id="R003",
        severity=Severity.WARNING,
        section_key=section_def.key,
        title=f"{section_def.title} 충족도 부족 ({section_status.coverage_ratio:.0%})",
        message=(
            f"{section_def.title} 섹션의 필수 지표 충족도가 "
            f"{section_status.coverage_ratio:.0%}로 50% 미만입니다. "
            f"추가 증거 수집을 권장합니다."
        ),
    )


def _rule_unsupported_claim_check(
    section_def: SectionDefinition,
    section_status: SectionStatus,
) -> QaIssue | None:
    """R004: 증거 없이 완료 상태인 섹션 검출 (unsupported claim 가능성).

    evidence가 0건인데 status가 complete로 표시되는 비정상 상태를 검출한다.
    """
    if (
        section_status.status == "complete"
        and section_status.total_evidence_count == 0
    ):
        return QaIssue(
            rule_id="R004",
            severity=Severity.CRITICAL,
            section_key=section_def.key,
            title=f"{section_def.title} 근거 없는 완료 상태 (unsupported claim)",
            message=(
                f"{section_def.title} 섹션이 완료 상태이지만 뒷받침하는 "
                f"증거 데이터가 없습니다. 근거 없는 주장(unsupported claim)이 "
                f"포함될 수 있습니다."
            ),
        )
    return None


def _rule_single_evidence_indicator(
    section_def: SectionDefinition,
    section_status: SectionStatus,
) -> list[QaIssue]:
    """R005: 단일 근거만 있는 지표 정보 제공."""
    issues: list[QaIssue] = []
    for ind in section_status.required_indicators:
        if ind.fulfilled and ind.evidence_count == 1:
            issues.append(QaIssue(
                rule_id="R005",
                severity=Severity.INFO,
                section_key=section_def.key,
                title=f"{section_def.title} — {ind.name} 근거 1건",
                message=(
                    f"{ind.name} 지표에 대한 근거가 1건뿐입니다. "
                    f"신뢰도 향상을 위해 추가 데이터 수집을 고려하세요."
                ),
                indicators=[ind.name],
            ))
    return issues


def _rule_required_section_missing(
    section_def: SectionDefinition,
    section_status: SectionStatus,
    project_type: str,
) -> QaIssue | None:
    """R007: 법적 필수 섹션 누락.

    사업유형 기반으로 필수 섹션에 증거가 전혀 없으면 critical 이슈를 발생한다.
    """
    if section_status.total_evidence_count > 0:
        return None

    required_keys = set(get_required_sections(project_type))
    if section_def.key not in required_keys:
        return None

    type_name = _get_project_type_name(project_type)
    req = REQUIRED_BY_TYPE.get(project_type)
    legal_basis = req.legal_basis if req else "환경영향평가법 시행령 별표 3"

    return QaIssue(
        rule_id="R007",
        severity=Severity.CRITICAL,
        section_key=section_def.key,
        title=f"{section_def.title} 법적 필수 섹션 누락",
        message=(
            f"{type_name} 사업은 {legal_basis}에 따라 "
            f"{section_def.title} 평가가 필수입니다. 데이터를 수집하세요."
        ),
        indicators=section_def.required_indicators,
        legal_basis=legal_basis,
    )


def _rule_required_indicator_missing(
    section_def: SectionDefinition,
    section_status: SectionStatus,
    project_type: str,
) -> list[QaIssue]:
    """R008: 법적 필수 지표 누락.

    필수 섹션 내에서 법적으로 요구되는 지표가 누락된 경우 warning 이슈를 발생한다.
    """
    issues: list[QaIssue] = []
    if section_status.total_evidence_count == 0:
        # R007에서 이미 처리됨
        return issues

    legal_indicators = get_required_indicators(project_type, section_def.key)
    if not legal_indicators:
        return issues

    # 실제 수집된 지표 집합
    fulfilled_set = {
        ind.name for ind in section_status.required_indicators if ind.fulfilled
    }

    missing_legal = [ind for ind in legal_indicators if ind not in fulfilled_set]
    if not missing_legal:
        return issues

    req = REQUIRED_BY_TYPE.get(project_type)
    legal_basis = req.legal_basis if req else "환경영향평가법 시행령 별표 3"

    issues.append(QaIssue(
        rule_id="R008",
        severity=Severity.WARNING,
        section_key=section_def.key,
        title=f"{section_def.title} 법적 필수 지표 누락 ({len(missing_legal)}건)",
        message=(
            f"{section_def.title} 섹션의 법적 필수 지표 "
            f"{', '.join(missing_legal)}이(가) 누락되었습니다."
        ),
        indicators=missing_legal,
        legal_basis=legal_basis,
    ))
    return issues


async def _rule_standards_exceedance(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_def: SectionDefinition,
) -> list[QaIssue]:
    """R006: 환경기준 초과 지표 검출.

    환경기준이 정의된 섹션에서 기준 초과 지표가 있으면 warning을 발생한다.
    """
    issues: list[QaIssue] = []

    section_check = await check_section_standards(db, project_id, section_def.key)
    if section_check is None or not section_check.has_exceedance:
        return issues

    fail_details: list[str] = []
    fail_indicators: list[str] = []
    for ind in section_check.indicators:
        if ind.status == CheckStatus.FAIL:
            fail_indicators.append(ind.indicator)
            unit = ind.standard_unit or ""
            avg_str = f"{ind.measured_avg:.4g}" if ind.measured_avg is not None else "?"
            std_str = f"{ind.standard_value:.4g}" if ind.standard_value is not None else "?"
            fail_details.append(
                f"{ind.indicator}: 측정 평균 {avg_str} {unit} "
                f"(기준 {std_str} {unit})"
            )

    if fail_details:
        issues.append(QaIssue(
            rule_id="R006",
            severity=Severity.WARNING,
            section_key=section_def.key,
            title=f"{section_def.title} 환경기준 초과 ({len(fail_details)}건)",
            message=(
                f"{section_def.title} 섹션에서 환경기준을 초과하는 지표가 "
                f"확인되었습니다: {'; '.join(fail_details)}. "
                f"저감대책 수립이 필요합니다."
            ),
            indicators=fail_indicators,
        ))

    return issues


# ────────────────────────────────────────────
# 메인 QA 실행
# ────────────────────────────────────────────

async def run_qa(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> QaResult:
    """프로젝트에 대해 전체 QA 규칙을 실행한다.

    사업유형(project_type)이 설정되어 있으면 required_items 기반으로
    R007/R008 법적 필수 항목 검증을 추가 수행한다.
    """
    all_issues: list[QaIssue] = []

    # 프로젝트 조회 → project_type 확인
    project = await get_project(db, project_id)
    project_type: str | None = None
    if project is not None:
        project_type = project.project_type

    # 사업유형 기반 필수 섹션 집합 (R001 동적 판단용)
    critical_sections = _get_critical_sections(project_type)
    required_section_keys = (
        set(get_required_sections(project_type)) if project_type else set()
    )

    for section_def in EIA_SECTIONS:
        section_status = await calculate_section_status(
            db, project_id, section_def.key
        )
        if section_status is None:
            continue

        is_legally_required = section_def.key in required_section_keys

        # R007: 법적 필수 섹션 누락 (사업유형 설정 시)
        if project_type and is_legally_required:
            issue = _rule_required_section_missing(
                section_def, section_status, project_type
            )
            if issue:
                all_issues.append(issue)

        # R001: 섹션 비어 있음 (법적 필수 섹션은 R007에서 처리)
        issue = _rule_section_empty(
            section_def, section_status, critical_sections,
            legally_required=is_legally_required and project_type is not None,
        )
        if issue:
            all_issues.append(issue)

        # R008: 법적 필수 지표 누락 (사업유형 설정 시)
        if project_type and is_legally_required:
            all_issues.extend(
                _rule_required_indicator_missing(
                    section_def, section_status, project_type
                )
            )

        # R002: 필수 지표 누락
        all_issues.extend(
            _rule_missing_required_indicators(
                section_def, section_status, critical_sections
            )
        )

        # R003: 충족도 부족
        issue = _rule_low_coverage(section_def, section_status)
        if issue:
            all_issues.append(issue)

        # R004: unsupported claim
        issue = _rule_unsupported_claim_check(section_def, section_status)
        if issue:
            all_issues.append(issue)

        # R005: 단일 근거 지표
        all_issues.extend(
            _rule_single_evidence_indicator(section_def, section_status)
        )

        # R006: 환경기준 초과
        all_issues.extend(
            await _rule_standards_exceedance(db, project_id, section_def)
        )

    # 요약 집계
    summary = QaSummary(
        critical_count=sum(1 for i in all_issues if i.severity == Severity.CRITICAL),
        warning_count=sum(1 for i in all_issues if i.severity == Severity.WARNING),
        info_count=sum(1 for i in all_issues if i.severity == Severity.INFO),
    )

    export_ready = summary.critical_count == 0

    return QaResult(
        project_id=str(project_id),
        run_at=datetime.now(tz=timezone.utc).isoformat(),
        issues=all_issues,
        summary=summary,
        export_ready=export_ready,
    )
