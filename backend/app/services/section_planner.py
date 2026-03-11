"""환경영향평가서 섹션 정의 및 상태 계산 서비스.

각 섹션은 evidence 카테고리와 매핑되며, 필수 지표(required_indicators) 목록을
기준으로 충족도를 계산한다. LLM 자유 작문 없이 evidence 기반으로만 동작한다.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import Evidence


# ────────────────────────────────────────────
# 섹션 정의
# ────────────────────────────────────────────

@dataclass(frozen=True)
class SectionDefinition:
    """EIA 평가서 섹션 정의."""

    key: str                          # 고유 키 (evidence category와 일치)
    title: str                        # 한글 제목
    description: str                  # 섹션 설명
    evidence_category: str            # 대응하는 evidence 카테고리
    required_indicators: list[str]    # 필수 지표 이름 목록
    order: int                        # 표시 순서


# 환경영향평가서 주요 섹션 정의 (환경영향평가법 시행령 기준 핵심 분야)
EIA_SECTIONS: list[SectionDefinition] = [
    SectionDefinition(
        key="air_quality",
        title="대기질",
        description="대기오염물질 현황 및 영향 예측",
        evidence_category="air_quality",
        required_indicators=[
            "PM10_연평균", "PM2.5_연평균", "NO2_연평균",
            "SO2_연평균", "CO_연평균", "O3_연평균",
        ],
        order=1,
    ),
    SectionDefinition(
        key="water_quality",
        title="수질",
        description="수질 현황 및 수계 영향 분석",
        evidence_category="water_quality",
        required_indicators=[
            "BOD", "COD", "SS", "T-N", "T-P", "DO",
        ],
        order=2,
    ),
    SectionDefinition(
        key="soil",
        title="토양",
        description="토양오염 현황 및 영향 분석",
        evidence_category="soil",
        required_indicators=[
            "중금속_납", "중금속_카드뮴", "유류오염_TPH", "pH",
        ],
        order=3,
    ),
    SectionDefinition(
        key="noise_vibration",
        title="소음·진동",
        description="소음 및 진동 현황과 영향 예측",
        evidence_category="noise_vibration",
        required_indicators=[
            "소음_Leq_주간", "소음_Leq_야간", "진동_Lv_주간",
        ],
        order=4,
    ),
    SectionDefinition(
        key="ecology",
        title="생태",
        description="동식물상 및 생태계 영향 분석",
        evidence_category="ecology",
        required_indicators=[
            "식물상_종수", "동물상_종수", "법정보호종",
            "비오톱_유형", "녹지자연도",
        ],
        order=5,
    ),
    SectionDefinition(
        key="land_use",
        title="토지이용",
        description="토지이용 현황 및 변화 분석",
        evidence_category="land_use",
        required_indicators=[
            "용도지역", "토지피복", "개발면적",
        ],
        order=6,
    ),
    SectionDefinition(
        key="traffic",
        title="교통",
        description="교통량 현황 및 영향 분석",
        evidence_category="traffic",
        required_indicators=[
            "교통량_현황", "서비스수준",
        ],
        order=7,
    ),
    SectionDefinition(
        key="waste",
        title="폐기물",
        description="폐기물 발생량 현황 및 관리 계획",
        evidence_category="waste",
        required_indicators=[
            "폐기물_발생량", "폐기물_종류",
        ],
        order=8,
    ),
    SectionDefinition(
        key="landscape",
        title="경관",
        description="경관 현황 및 시각적 영향 분석",
        evidence_category="landscape",
        required_indicators=[
            "주요_조망점", "경관_유형",
        ],
        order=9,
    ),
    SectionDefinition(
        key="cultural_heritage",
        title="문화재",
        description="문화재 현황 및 영향 분석",
        evidence_category="cultural_heritage",
        required_indicators=[
            "문화재_목록", "이격거리",
        ],
        order=10,
    ),
    SectionDefinition(
        key="climate",
        title="기후",
        description="기후 현황 및 온실가스 영향 분석",
        evidence_category="climate",
        required_indicators=[
            "기온_연평균", "강수량_연평균", "풍향_풍속",
        ],
        order=11,
    ),
]

# 빠른 조회용 딕셔너리
_SECTION_MAP: dict[str, SectionDefinition] = {s.key: s for s in EIA_SECTIONS}


def get_section_definitions() -> list[SectionDefinition]:
    """전체 섹션 정의 목록 반환."""
    return list(EIA_SECTIONS)


def get_section_definition(section_key: str) -> SectionDefinition | None:
    """단일 섹션 정의 조회."""
    return _SECTION_MAP.get(section_key)


# ────────────────────────────────────────────
# 섹션 상태 계산
# ────────────────────────────────────────────

@dataclass
class IndicatorStatus:
    """개별 지표의 충족 상태."""

    name: str
    fulfilled: bool = False
    evidence_count: int = 0


@dataclass
class SectionStatus:
    """섹션의 증거 충족 상태."""

    section_key: str
    title: str
    description: str
    order: int
    total_evidence_count: int = 0           # 해당 카테고리 전체 evidence 수
    required_indicators: list[IndicatorStatus] = field(default_factory=list)
    fulfilled_count: int = 0                # 충족된 필수 지표 수
    required_count: int = 0                 # 전체 필수 지표 수
    coverage_ratio: float = 0.0             # 충족도 (0.0 ~ 1.0)
    status: str = "empty"                   # empty / partial / complete


async def calculate_section_status(
    db: AsyncSession,
    project_id: uuid.UUID,
    section_key: str,
) -> SectionStatus | None:
    """단일 섹션의 증거 충족 상태를 계산한다.

    screening_only=False인 본 평가 데이터만 대상으로 한다.
    """
    section_def = get_section_definition(section_key)
    if section_def is None:
        return None

    # 해당 카테고리 + 본 평가 데이터 조회
    base_filter = (
        (Evidence.project_id == project_id)
        & (Evidence.category == section_def.evidence_category)
        & (Evidence.screening_only.is_(False))
    )

    # 전체 evidence 수
    count_result = await db.execute(
        select(func.count()).select_from(Evidence).where(base_filter)
    )
    total_count = count_result.scalar_one()

    # 지표별 evidence 수 집계
    indicator_counts_result = await db.execute(
        select(Evidence.indicator, func.count())
        .where(base_filter)
        .group_by(Evidence.indicator)
    )
    indicator_counts: dict[str, int] = dict(indicator_counts_result.all())

    # 필수 지표 충족 상태 계산
    indicator_statuses = []
    fulfilled = 0
    for ind_name in section_def.required_indicators:
        count = indicator_counts.get(ind_name, 0)
        is_fulfilled = count > 0
        if is_fulfilled:
            fulfilled += 1
        indicator_statuses.append(IndicatorStatus(
            name=ind_name,
            fulfilled=is_fulfilled,
            evidence_count=count,
        ))

    required_total = len(section_def.required_indicators)
    ratio = fulfilled / required_total if required_total > 0 else 0.0

    # 상태 결정
    if total_count == 0:
        status_label = "empty"
    elif fulfilled >= required_total:
        status_label = "complete"
    else:
        status_label = "partial"

    return SectionStatus(
        section_key=section_def.key,
        title=section_def.title,
        description=section_def.description,
        order=section_def.order,
        total_evidence_count=total_count,
        required_indicators=indicator_statuses,
        fulfilled_count=fulfilled,
        required_count=required_total,
        coverage_ratio=round(ratio, 4),
        status=status_label,
    )


async def calculate_all_sections_status(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[SectionStatus]:
    """프로젝트의 전체 섹션 충족 상태를 계산한다."""
    results = []
    for section_def in EIA_SECTIONS:
        section_status = await calculate_section_status(
            db, project_id, section_def.key
        )
        if section_status is not None:
            results.append(section_status)
    return results
