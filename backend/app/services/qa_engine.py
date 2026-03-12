"""결정적 QA 규칙 엔진.

섹션별 필수 증거 누락 검사, unsupported claim 검출, 심각도 등급 판정을 수행한다.
규칙은 결정적(deterministic)으로 동작하며 LLM을 사용하지 않는다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.section_planner import (
    EIA_SECTIONS,
    SectionDefinition,
    calculate_section_status,
    SectionStatus,
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
# 핵심 섹션 정의 (이 섹션들은 evidence가 전혀 없으면 critical)
# ────────────────────────────────────────────

_CRITICAL_SECTIONS = {
    "air_quality", "water_quality", "noise_vibration", "ecology",
}


# ────────────────────────────────────────────
# 규칙 함수들
# ────────────────────────────────────────────

def _rule_section_empty(
    section_def: SectionDefinition,
    section_status: SectionStatus,
) -> QaIssue | None:
    """R001: 섹션에 증거가 전혀 없는 경우."""
    if section_status.total_evidence_count > 0:
        return None

    # 핵심 섹션이면 critical, 아니면 warning
    is_critical = section_def.key in _CRITICAL_SECTIONS
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
) -> list[QaIssue]:
    """R002: 필수 지표 누락 검사."""
    issues: list[QaIssue] = []
    if section_status.total_evidence_count == 0:
        # R001에서 이미 처리됨
        return issues

    missing = [
        ind.name
        for ind in section_status.required_indicators
        if not ind.fulfilled
    ]
    if not missing:
        return issues

    # 핵심 섹션이면 critical, 아니면 warning
    is_critical = section_def.key in _CRITICAL_SECTIONS
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


# ────────────────────────────────────────────
# 메인 QA 실행
# ────────────────────────────────────────────

async def run_qa(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> QaResult:
    """프로젝트에 대해 전체 QA 규칙을 실행한다."""
    all_issues: list[QaIssue] = []

    for section_def in EIA_SECTIONS:
        section_status = await calculate_section_status(
            db, project_id, section_def.key
        )
        if section_status is None:
            continue

        # R001: 섹션 비어 있음
        issue = _rule_section_empty(section_def, section_status)
        if issue:
            all_issues.append(issue)

        # R002: 필수 지표 누락
        all_issues.extend(
            _rule_missing_required_indicators(section_def, section_status)
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
