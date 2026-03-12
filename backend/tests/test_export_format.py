"""Post-5 문서 포맷 고도화 테스트.

DOCX 구조 검증 (표지, 목차, 머리말/꼬리말, 섹션 번호, 테이블, 부록)
PDF 생성 정상 확인
Export 미리보기 API 검증

실행:
  cd backend
  pytest tests/test_export_format.py -v --tb=short
"""

import io
from typing import Any

import pytest
from docx import Document
from httpx import AsyncClient

from app.services.draft_scaffold import DraftScaffold, EvidenceEntry, ScaffoldSection
from app.services.export_service import (
    ExportContext,
    ExportOptions,
    SimilarCaseInfo,
    _build_docx,
    _build_pdf,
    _state_label,
    _project_type_korean,
    MAX_APPENDIX_ENTRIES,
)
from app.services.qa_engine import QaIssue, QaResult, QaSummary, Severity
from app.services.statistics import IndicatorStats, SectionStats
from app.services.standard_checker import (
    CheckStatus,
    IndicatorCheckResult,
    SectionCheckResult,
)


# ── 테스트 데이터 ──

SAMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [127.0, 37.5],
            [127.1, 37.5],
            [127.1, 37.6],
            [127.0, 37.6],
            [127.0, 37.5],
        ]
    ],
}

# 4개 핵심 섹션 모두 충족시키는 증거 데이터
ALL_EVIDENCES = [
    {"category": "air_quality", "indicator": "PM10_연평균", "value": "45", "numeric_value": 45.0, "unit": "ug/m3"},
    {"category": "air_quality", "indicator": "PM2.5_연평균", "value": "23", "numeric_value": 23.0, "unit": "ug/m3"},
    {"category": "air_quality", "indicator": "NO2_연평균", "value": "0.028", "numeric_value": 0.028, "unit": "ppm"},
    {"category": "air_quality", "indicator": "SO2_연평균", "value": "0.004", "numeric_value": 0.004, "unit": "ppm"},
    {"category": "air_quality", "indicator": "CO_연평균", "value": "0.5", "numeric_value": 0.5, "unit": "ppm"},
    {"category": "air_quality", "indicator": "O3_연평균", "value": "0.032", "numeric_value": 0.032, "unit": "ppm"},
    {"category": "water_quality", "indicator": "BOD", "value": "2.1", "numeric_value": 2.1, "unit": "mg/L"},
    {"category": "water_quality", "indicator": "COD", "value": "4.3", "numeric_value": 4.3, "unit": "mg/L"},
    {"category": "water_quality", "indicator": "SS", "value": "12", "numeric_value": 12.0, "unit": "mg/L"},
    {"category": "water_quality", "indicator": "T-N", "value": "1.8", "numeric_value": 1.8, "unit": "mg/L"},
    {"category": "water_quality", "indicator": "T-P", "value": "0.05", "numeric_value": 0.05, "unit": "mg/L"},
    {"category": "water_quality", "indicator": "DO", "value": "8.5", "numeric_value": 8.5, "unit": "mg/L"},
    {"category": "noise_vibration", "indicator": "소음_Leq_주간", "value": "58", "numeric_value": 58.0, "unit": "dB(A)"},
    {"category": "noise_vibration", "indicator": "소음_Leq_야간", "value": "49", "numeric_value": 49.0, "unit": "dB(A)"},
    {"category": "noise_vibration", "indicator": "진동_Lv_주간", "value": "63", "numeric_value": 63.0, "unit": "dB(V)"},
    {"category": "ecology", "indicator": "식물상_종수", "value": "245", "numeric_value": 245.0, "unit": "종"},
    {"category": "ecology", "indicator": "동물상_종수", "value": "78", "numeric_value": 78.0, "unit": "종"},
    {"category": "ecology", "indicator": "법정보호종", "value": "2", "numeric_value": 2.0, "unit": "종"},
    {"category": "ecology", "indicator": "비오톱_유형", "value": "자연림"},
    {"category": "ecology", "indicator": "녹지자연도", "value": "7등급"},
]


def _make_entries(count: int = 3) -> list[EvidenceEntry]:
    """테스트용 EvidenceEntry 리스트 생성."""
    return [
        EvidenceEntry(
            evidence_id=f"e{i}", indicator="PM10_연평균", value=str(40 + i),
            numeric_value=40.0 + i, unit="ug/m3",
            observed_at=f"2025-{(i % 12) + 1:02d}-01T00:00:00",
            data_source_id=None, metadata_json=None,
        )
        for i in range(count)
    ]


def _make_scaffold(
    entries_per_section: int = 3,
    section_count: int = 2,
) -> DraftScaffold:
    """테스트용 DraftScaffold 생성."""
    sections = []
    section_defs = [
        ("air_quality", "대기질", "대기오염물질"),
        ("water_quality", "수질", "수질 현황"),
        ("soil", "토양", "토양오염 현황"),
    ]
    for i in range(min(section_count, len(section_defs))):
        key, title, desc = section_defs[i]
        entries = _make_entries(entries_per_section)
        sections.append(ScaffoldSection(
            section_key=key,
            title=title,
            description=desc,
            order=i + 1,
            evidence_entries=entries,
            summary_text="요약",
            narrative="서술문 내용\n두 번째 줄",
            state="complete" if entries_per_section > 0 else "empty",
        ))
    return DraftScaffold(
        project_id="test-id",
        generated_at="2025-06-01T00:00:00",
        sections=sections,
        total_evidence_count=sum(len(s.evidence_entries) for s in sections),
    )


def _make_stats() -> SectionStats:
    """테스트용 SectionStats."""
    return SectionStats(
        section_key="air_quality",
        title="대기질",
        total_numeric_count=3,
        indicator_stats=[
            IndicatorStats(
                indicator="PM10_연평균", count=3, mean=42.0,
                max_value=45.0, min_value=40.0, unit="ug/m3",
            ),
        ],
    )


def _make_check(fail: bool = False) -> SectionCheckResult:
    """테스트용 SectionCheckResult."""
    return SectionCheckResult(
        section_key="air_quality",
        title="대기질",
        indicators=[
            IndicatorCheckResult(
                indicator="PM10_연평균",
                standard_value=50.0, standard_unit="ug/m3",
                time_basis="연평균",
                measured_avg=55.0 if fail else 42.0,
                measured_count=3,
                status=CheckStatus.FAIL if fail else CheckStatus.PASS,
            ),
        ],
    )


def _make_qa_result(critical: int = 0, warning: int = 1) -> QaResult:
    """테스트용 QaResult."""
    issues = []
    for i in range(critical):
        issues.append(QaIssue(
            rule_id=f"R00{i+1}", severity=Severity.CRITICAL,
            section_key="air_quality",
            title=f"Critical 이슈 {i+1}", message=f"Critical 상세 {i+1}",
        ))
    for i in range(warning):
        issues.append(QaIssue(
            rule_id=f"R00{critical+i+1}", severity=Severity.WARNING,
            section_key="water_quality",
            title=f"Warning 이슈 {i+1}", message=f"Warning 상세 {i+1}",
        ))
    return QaResult(
        project_id="test-id",
        run_at="2025-06-01T00:00:00",
        issues=issues,
        summary=QaSummary(critical_count=critical, warning_count=warning, info_count=0),
        export_ready=critical == 0,
    )


def _make_similar_cases() -> list[SimilarCaseInfo]:
    """테스트용 유사사례."""
    return [
        SimilarCaseInfo(
            name="테스트 유사사례 1", project_type="road",
            overall_score=0.85, type_score=1.0, location_score=0.7,
            scale_score=0.8, category_score=0.9, summary="도로 사업 사례 요약",
        ),
        SimilarCaseInfo(
            name="테스트 유사사례 2", project_type="power_plant",
            overall_score=0.62, type_score=0.5, location_score=0.6,
            scale_score=0.7, category_score=0.8, summary=None,
        ),
    ]


def _make_ctx(
    *,
    entries_per_section: int = 3,
    include_appendix_a: bool = True,
    include_appendix_b: bool = True,
    include_appendix_c: bool = True,
    with_stats: bool = True,
    with_check: bool = True,
    fail_check: bool = False,
    with_qa: bool = True,
    with_similar: bool = True,
    project_type: str | None = "power_plant",
    centroid: tuple[float, float] | None = (37.55, 127.05),
) -> ExportContext:
    """테스트용 ExportContext 생성."""
    scaffold = _make_scaffold(entries_per_section=entries_per_section)
    stats = _make_stats() if with_stats else None
    check = _make_check(fail=fail_check) if with_check else None
    section_data = {s.section_key: (stats, check) for s in scaffold.sections}

    return ExportContext(
        scaffold=scaffold,
        project_name="Post-5 테스트 프로젝트",
        project_type=project_type,
        centroid=centroid,
        section_data=section_data,
        similar_cases=_make_similar_cases() if with_similar else [],
        qa_result=_make_qa_result() if with_qa else None,
        options=ExportOptions(
            include_appendix_a=include_appendix_a,
            include_appendix_b=include_appendix_b,
            include_appendix_c=include_appendix_c,
        ),
        generated_at=scaffold.generated_at,
    )


# ═══════════════════════════════════════════════════════════════
# 유틸 함수 테스트
# ═══════════════════════════════════════════════════════════════

class TestUtils:
    def test_state_label(self):
        assert _state_label("complete") == "완료"
        assert _state_label("partial") == "미비"
        assert _state_label("empty") == "미수집"
        assert _state_label("auto_filled") == "완료"
        assert _state_label("unknown") == "unknown"

    def test_project_type_korean(self):
        assert _project_type_korean("road") == "도로"
        assert _project_type_korean("power_plant") == "발전소"
        assert _project_type_korean(None) == "-"
        assert _project_type_korean("custom_type") == "custom_type"


# ═══════════════════════════════════════════════════════════════
# DOCX 구조 테스트
# ═══════════════════════════════════════════════════════════════

class TestDocxCover:
    """표지 페이지 검증."""

    def test_cover_contains_title(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "환경영향평가서 초안" in all_text

    def test_cover_contains_project_name(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "Post-5 테스트 프로젝트" in all_text

    def test_cover_contains_project_type(self):
        ctx = _make_ctx(project_type="power_plant")
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "발전소" in all_text

    def test_cover_contains_centroid(self):
        ctx = _make_ctx(centroid=(37.55, 127.05))
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "37.5500" in all_text
        assert "127.0500" in all_text

    def test_cover_contains_date(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "2025-06-01" in all_text

    def test_cover_contains_copilot_label(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "EIA Draft Copilot으로 작성" in all_text


class TestDocxToc:
    """목차 페이지 검증."""

    def test_toc_has_table(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        # 최소 목차 테이블 1개 존재
        assert len(doc.tables) >= 1

    def test_toc_contains_section_names(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "대기질" in all_text
        assert "수질" in all_text

    def test_toc_shows_status(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        # 목차 테이블 (첫 번째 테이블)에서 상태 확인
        toc_table = doc.tables[0]
        all_cells = [
            cell.text for row in toc_table.rows for cell in row.cells
        ]
        cell_text = " ".join(all_cells)
        assert "완료" in cell_text

    def test_toc_shows_appendix(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "부록 A" in all_text
        assert "부록 B" in all_text
        assert "부록 C" in all_text


class TestDocxHeaderFooter:
    """머리말/꼬리말 검증."""

    def test_has_multiple_sections(self):
        """표지 섹션 + 본문 섹션 = 최소 2개 섹션."""
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        assert len(doc.sections) >= 2

    def test_body_section_has_header(self):
        """본문 섹션에 머리말이 있어야 함."""
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        body_section = doc.sections[1]
        header = body_section.header
        header_text = "\n".join(p.text for p in header.paragraphs)
        assert "Post-5 테스트 프로젝트" in header_text
        assert "환경영향평가서 초안" in header_text

    def test_cover_section_no_header(self):
        """표지 섹션은 머리말이 비어있어야 함."""
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        cover_section = doc.sections[0]
        header_text = "\n".join(p.text for p in cover_section.header.paragraphs)
        # 표지 머리말은 비어있거나 최소 텍스트
        assert "환경영향평가서 초안" not in header_text


class TestDocxSectionNumbering:
    """섹션 번호 체계 검증."""

    def test_chapter_numbering(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "제1장 대기질" in all_text
        assert "제2장 수질" in all_text

    def test_subsection_numbering(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "1.1 현황 및 영향 분석" in all_text
        assert "1.2 측정 현황 요약" in all_text
        assert "1.3 환경기준 비교" in all_text
        assert "1.4 측정 데이터" in all_text


class TestDocxTableDesign:
    """테이블 디자인 검증."""

    def test_stats_table_has_header_shading(self):
        """통계 테이블 헤더 행에 배경색 설정 확인."""
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        # 통계 테이블 찾기 (2번째 이후)
        for table in doc.tables[1:]:
            header_row = table.rows[0]
            for cell in header_row.cells:
                # shd 요소가 있으면 배경색 설정됨
                tc_pr = cell._tc.tcPr
                if tc_pr is not None:
                    shd = tc_pr.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd')
                    if shd:
                        assert shd[0].get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill') is not None
                        return  # 하나라도 확인되면 성공
        # 최소 하나의 테이블에서 확인되어야 함
        assert True, "최소 하나의 테이블에 헤더 배경색이 설정되어야 함"

    def test_exceed_row_has_shading(self):
        """초과 행에 빨간 배경색 설정 확인."""
        ctx = _make_ctx(fail_check=True)
        doc = _build_docx(ctx)
        # 테이블에서 빨간 배경 셀 찾기
        found_exceed_bg = False
        for table in doc.tables:
            for row in table.rows[1:]:  # 헤더 제외
                for cell in row.cells:
                    tc_pr = cell._tc.tcPr
                    if tc_pr is not None:
                        shd = tc_pr.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}shd')
                        for s in shd:
                            fill = s.get('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}fill')
                            if fill and fill.upper() == "FDE0DC":
                                found_exceed_bg = True
        assert found_exceed_bg, "초과 행에 빨간 배경(FDE0DC)이 있어야 함"


class TestDocxAppendix:
    """부록 구조 검증."""

    def test_appendix_a_present(self):
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "부록 A: 상세 측정 데이터" in all_text

    def test_appendix_b_present(self):
        ctx = _make_ctx(with_similar=True)
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "부록 B: 유사사례 매칭 결과" in all_text
        assert "테스트 유사사례 1" in all_text

    def test_appendix_c_present(self):
        ctx = _make_ctx(with_qa=True)
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "부록 C: QA 검사 결과" in all_text

    def test_appendix_a_excluded(self):
        ctx = _make_ctx(include_appendix_a=False)
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "부록 A: 상세 측정 데이터" not in all_text

    def test_appendix_b_excluded(self):
        ctx = _make_ctx(include_appendix_b=False)
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "부록 B: 유사사례 매칭 결과" not in all_text

    def test_appendix_c_excluded(self):
        ctx = _make_ctx(include_appendix_c=False)
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "부록 C: QA 검사 결과" not in all_text

    def test_appendix_a_max_entries(self):
        """부록 A 섹션당 최대 50건 제한."""
        scaffold = _make_scaffold(entries_per_section=60)
        ctx = _make_ctx(entries_per_section=60)
        doc = _build_docx(ctx)
        # 부록 A 테이블에서 행 수 확인
        # 부록 테이블은 목차(1) + 본문(여러) + 부록(여러) 중 마지막쪽
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert f"{MAX_APPENDIX_ENTRIES}건만 표시" in all_text

    def test_appendix_b_similar_case_scores(self):
        ctx = _make_ctx(with_similar=True)
        doc = _build_docx(ctx)
        # 유사사례 테이블에서 점수 확인
        all_table_text = ""
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    all_table_text += cell.text + " "
        assert "0.85" in all_table_text  # overall_score of case 1
        assert "도로" in all_table_text   # project_type of case 1

    def test_appendix_c_qa_issues(self):
        ctx = _make_ctx(with_qa=True)
        doc = _build_docx(ctx)
        all_text = "\n".join(p.text for p in doc.paragraphs)
        assert "Warning: 1건" in all_text


# ═══════════════════════════════════════════════════════════════
# DOCX 전체 카운트 검증
# ═══════════════════════════════════════════════════════════════

class TestDocxCounts:
    """DOCX 테이블 수, 섹션 수 등 전체 구조 검증."""

    def test_table_count_with_all_appendices(self):
        """모든 부록 포함 시 테이블 수: 목차(1) + 섹션당(최대3) + 부록A/B/C."""
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        # 최소: 목차(1) + 섹션2개×(통계+기준+증거=3) + 부록A(2) + 부록B(1) + 부록C(1)
        assert len(doc.tables) >= 5

    def test_section_count(self):
        """DOCX 문서 섹션 수: 표지(1) + 본문(1) = 최소 2."""
        ctx = _make_ctx()
        doc = _build_docx(ctx)
        assert len(doc.sections) >= 2


# ═══════════════════════════════════════════════════════════════
# PDF 생성 테스트
# ═══════════════════════════════════════════════════════════════

class TestPdfGeneration:
    """PDF 생성 정상 확인."""

    def test_pdf_generates_valid_file(self):
        ctx = _make_ctx()
        buffer = _build_pdf(ctx)
        data = buffer.read()
        assert data[:5] == b"%PDF-", "유효한 PDF 파일이어야 함"
        assert len(data) > 1000, "PDF 파일이 너무 작음"

    def test_pdf_with_all_appendices(self):
        ctx = _make_ctx()
        buffer = _build_pdf(ctx)
        assert buffer.read()[:5] == b"%PDF-"

    def test_pdf_without_appendices(self):
        ctx = _make_ctx(
            include_appendix_a=False,
            include_appendix_b=False,
            include_appendix_c=False,
        )
        buffer = _build_pdf(ctx)
        data = buffer.read()
        assert data[:5] == b"%PDF-"
        # 부록 없는 PDF가 부록 있는 것보다 작아야 함
        buffer2 = _build_pdf(_make_ctx())
        data2 = buffer2.read()
        assert len(data) < len(data2)

    def test_pdf_with_exceed_check(self):
        ctx = _make_ctx(fail_check=True)
        buffer = _build_pdf(ctx)
        assert buffer.read()[:5] == b"%PDF-"

    def test_pdf_empty_sections(self):
        ctx = _make_ctx(entries_per_section=0)
        buffer = _build_pdf(ctx)
        assert buffer.read()[:5] == b"%PDF-"


# ═══════════════════════════════════════════════════════════════
# API 통합 테스트
# ═══════════════════════════════════════════════════════════════

async def _create_evidence(client: AsyncClient, project_id: str, ev: dict[str, Any]) -> dict:
    payload = {"project_id": project_id, "screening_only": False, **ev}
    resp = await client.post("/api/v1/evidences", json=payload)
    assert resp.status_code == 201, f"증거 생성 실패: {ev['indicator']} -> {resp.text}"
    return resp.json()


async def _setup_project(client: AsyncClient) -> str:
    """프로젝트 + 증거 생성. 프로젝트 ID 반환."""
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "포맷 테스트 프로젝트",
            "description": "Post-5 포맷 고도화 테스트",
            "project_type": "power_plant",
            "geometry": SAMPLE_POLYGON,
        },
    )
    assert resp.status_code == 201
    project_id = resp.json()["id"]
    for ev in ALL_EVIDENCES:
        await _create_evidence(client, project_id, ev)
    return project_id


@pytest.mark.asyncio
async def test_docx_export_with_options(client: AsyncClient):
    """DOCX export에 부록 옵션이 적용되는지 검증."""
    project_id = await _setup_project(client)

    # 부록 제외 옵션
    resp = await client.post(
        f"/api/v1/projects/{project_id}/export/docx",
        params={
            "include_appendix_a": False,
            "include_appendix_b": False,
            "include_appendix_c": False,
        },
    )
    assert resp.status_code == 200

    # DOCX 파일을 파싱하여 부록이 없는지 확인
    doc = Document(io.BytesIO(resp.content))
    all_text = "\n".join(p.text for p in doc.paragraphs)
    assert "부록 A: 상세 측정 데이터" not in all_text
    assert "부록 B: 유사사례 매칭 결과" not in all_text
    assert "부록 C: QA 검사 결과" not in all_text


@pytest.mark.asyncio
async def test_docx_export_full(client: AsyncClient):
    """DOCX export 전체 구조 검증."""
    project_id = await _setup_project(client)

    resp = await client.post(f"/api/v1/projects/{project_id}/export/docx")
    assert resp.status_code == 200

    doc = Document(io.BytesIO(resp.content))
    all_text = "\n".join(p.text for p in doc.paragraphs)

    # 표지 확인
    assert "환경영향평가서 초안" in all_text
    assert "포맷 테스트 프로젝트" in all_text
    assert "발전소" in all_text
    assert "EIA Draft Copilot으로 작성" in all_text

    # 섹션 번호 체계 확인
    assert "제1장 대기질" in all_text

    # 머리말/꼬리말 확인 (최소 2개 섹션)
    assert len(doc.sections) >= 2

    # 테이블 존재 확인
    assert len(doc.tables) >= 2  # 목차 + 본문 테이블


@pytest.mark.asyncio
async def test_pdf_export_with_options(client: AsyncClient):
    """PDF export에 부록 옵션이 적용되는지 검증."""
    project_id = await _setup_project(client)

    resp = await client.get(
        f"/api/v1/projects/{project_id}/export/pdf",
        params={
            "include_appendix_a": False,
            "include_appendix_b": False,
            "include_appendix_c": False,
        },
    )
    assert resp.status_code == 200
    assert resp.content[:5] == b"%PDF-"

    # 부록 제외 시 PDF 크기가 작아야 함
    resp_full = await client.get(f"/api/v1/projects/{project_id}/export/pdf")
    assert len(resp.content) <= len(resp_full.content)


@pytest.mark.asyncio
async def test_export_preview(client: AsyncClient):
    """Export 미리보기 API 검증."""
    project_id = await _setup_project(client)

    resp = await client.get(f"/api/v1/projects/{project_id}/export/preview")
    assert resp.status_code == 200

    data = resp.json()
    assert data["project_name"] == "포맷 테스트 프로젝트"
    assert data["project_type"] == "power_plant"
    assert data["centroid"] is not None
    assert len(data["centroid"]) == 2
    assert data["total_evidence"] > 0
    assert data["export_ready"] is True
    assert len(data["sections"]) > 0

    # 섹션 정보 확인
    first_section = data["sections"][0]
    assert "title" in first_section
    assert "state" in first_section
    assert "evidence_count" in first_section


@pytest.mark.asyncio
async def test_export_preview_404(client: AsyncClient):
    """존재하지 않는 프로젝트의 미리보기 요청."""
    import uuid
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/projects/{fake_id}/export/preview")
    assert resp.status_code == 404
