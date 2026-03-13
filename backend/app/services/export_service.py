"""DOCX/PDF 출력 서비스.

초안 뼈대(DraftScaffold) 데이터를 기반으로 DOCX 및 PDF 문서를 생성한다.
- DOCX: python-docx 사용
- PDF: reportlab 사용 (한글 폰트 지원)

Post-5 전면 개편:
- 표지 페이지: 사업명, 사업 유형, 사업 위치(geometry 중심점), 작성일
- 목차: 충족도 상태 표시 (완료/미비/미수집)
- 머리말/꼬리말: 사업명 + 문서 제목 / 페이지 번호
- 섹션 번호 체계: "제1장 대기질" → "1.1 현황" → "1.2 측정" → "1.3 기준비교"
- 테이블 디자인: 헤더 배경색, 초과 셀 빨간 배경, 열 너비 조정
- 부록 A/B/C: 상세 데이터, 유사사례, QA 결과
"""

from __future__ import annotations

import io
import os
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Emu, Mm, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.services.draft_scaffold import (
    DraftScaffold,
    EvidenceEntry,
    ScaffoldSection,
    generate_draft_scaffold,
    MAX_DETAIL_SAMPLES,
)
from app.services.qa_engine import QaResult, run_qa
from app.services.standard_checker import (
    CheckStatus,
    check_section_standards,
)
from app.services.statistics import calculate_section_statistics


# ── 공통 상수 ──

# 부록 A에서 섹션당 최대 데이터 건수
MAX_APPENDIX_ENTRIES = 50

# 사업 유형 한글 매핑
PROJECT_TYPE_NAMES: dict[str, str] = {
    "road": "도로",
    "railway": "철도",
    "airport": "공항",
    "port": "항만",
    "power_plant": "발전소",
    "industrial": "산업단지",
    "housing": "주거단지",
    "reclamation": "매립",
    "dam": "댐",
    "other": "기타",
}

# DOCX 테이블 색상
_HEADER_BG = "D6E4F0"         # 연한 파란색 (헤더 행)
_EXCEED_BG = "FDE0DC"         # 연한 빨간색 (초과 셀)
_ALT_ROW_BG = "F5F5F7"       # 교차 행 배경


# ── 공통 데이터 구조 ──

@dataclass
class ExportOptions:
    """Export 옵션."""

    include_appendix_a: bool = True   # 부록 A: 상세 측정 데이터
    include_appendix_b: bool = True   # 부록 B: 유사사례 매칭 결과
    include_appendix_c: bool = True   # 부록 C: QA 검사 결과
    include_detail_data: bool = True  # 본문 내 상세 데이터 포함


@dataclass
class SimilarCaseInfo:
    """부록 B용 유사사례 요약 정보."""

    name: str
    project_type: str
    overall_score: float
    type_score: float
    location_score: float
    scale_score: float
    category_score: float
    summary: str | None = None


@dataclass
class ExportContext:
    """Export 시 필요한 모든 데이터를 담는 컨텍스트."""

    scaffold: DraftScaffold
    project_name: str
    project_type: str | None
    centroid: tuple[float, float] | None    # (위도, 경도)
    section_data: dict                       # {section_key: (stats, check)}
    similar_cases: list[SimilarCaseInfo]
    qa_result: QaResult | None
    options: ExportOptions
    generated_at: str                        # ISO 문자열


# ── 공통 유틸 ──

def _get_centroid_coords(geometry_wkb) -> tuple[float, float] | None:
    """geometry WKB → (위도, 경도) centroid 좌표."""
    if geometry_wkb is None:
        return None
    try:
        from geoalchemy2.shape import to_shape
        shape = to_shape(geometry_wkb)
        centroid = shape.centroid
        return (round(centroid.y, 6), round(centroid.x, 6))
    except Exception:
        return None


def _state_label(state: str) -> str:
    """섹션 상태를 한글 레이블로 변환."""
    labels = {
        "complete": "완료",
        "auto_filled": "완료",
        "partial": "미비",
        "empty": "미수집",
    }
    return labels.get(state, state)


def _project_type_korean(project_type: str | None) -> str:
    """사업 유형을 한글로 변환."""
    if project_type is None:
        return "-"
    return PROJECT_TYPE_NAMES.get(project_type, project_type)


async def _build_export_context(
    db: AsyncSession,
    project: Project,
    *,
    options: ExportOptions | None = None,
    qa_result: QaResult | None = None,
) -> ExportContext:
    """Export에 필요한 모든 데이터를 수집하여 ExportContext를 구성한다."""
    opts = options or ExportOptions()

    # 초안 뼈대 생성
    scaffold = await generate_draft_scaffold(db, project.id)

    # 섹션별 통계/기준비교 데이터
    section_data = {}
    for section in scaffold.sections:
        stats = await calculate_section_statistics(
            db, project.id, section.section_key
        )
        check = await check_section_standards(
            db, project.id, section.section_key
        )
        section_data[section.section_key] = (stats, check)

    # 유사사례 매칭 (부록 B)
    similar_cases: list[SimilarCaseInfo] = []
    if opts.include_appendix_b:
        try:
            from app.services.similarity import find_similar_cases
            categories = {
                s.section_key for s in scaffold.sections
                if s.evidence_entries
            }
            match_result = await find_similar_cases(
                db, project.id,
                evidence_categories=categories,
                top_k=10,
            )
            # 유사사례 중복 제거 (이름 기준, 점수 높은 것 우선)
            seen_names: set[str] = set()
            for m in match_result.matches:
                if m.similar_case.name in seen_names:
                    continue
                seen_names.add(m.similar_case.name)
                similar_cases.append(SimilarCaseInfo(
                    name=m.similar_case.name,
                    project_type=m.similar_case.project_type,
                    overall_score=m.overall_score,
                    type_score=m.type_score,
                    location_score=m.location_score,
                    scale_score=m.scale_score,
                    category_score=m.category_score,
                    summary=m.similar_case.summary,
                ))
        except Exception:
            pass  # 유사사례 데이터 없어도 export 진행

    # geometry centroid
    centroid = _get_centroid_coords(project.geometry)

    return ExportContext(
        scaffold=scaffold,
        project_name=project.name,
        project_type=project.project_type,
        centroid=centroid,
        section_data=section_data,
        similar_cases=similar_cases,
        qa_result=qa_result,
        options=opts,
        generated_at=scaffold.generated_at,
    )


# ═══════════════════════════════════════════════════════════════
# DOCX 출력
# ═══════════════════════════════════════════════════════════════

async def generate_docx(
    db: AsyncSession,
    project: Project,
    *,
    options: ExportOptions | None = None,
    skip_qa_check: bool = False,
) -> tuple[io.BytesIO, str]:
    """DOCX 문서를 생성하여 BytesIO와 파일명을 반환한다.

    Args:
        db: DB 세션
        project: 프로젝트 ORM 객체
        options: Export 옵션 (부록 포함 여부 등)
        skip_qa_check: True면 QA 검사를 건너뜀 (테스트용)

    Returns:
        (BytesIO 버퍼, 파일명) 튜플

    Raises:
        ValueError: critical QA 이슈가 있어 export가 차단된 경우
    """
    qa_result = None
    if not skip_qa_check:
        qa_result = await run_qa(db, project.id)
        if not qa_result.export_ready:
            raise ValueError(
                f"critical 이슈 {qa_result.summary.critical_count}건이 "
                f"남아 있어 export가 차단되었습니다."
            )

    ctx = await _build_export_context(
        db, project,
        options=options,
        qa_result=qa_result,
    )

    doc = _build_docx(ctx)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(
        c if c.isascii() and c.isalnum() or c in "-_" else "_"
        for c in project.name.replace(" ", "_")
    )[:50].strip("_") or "draft"
    filename = f"EIA_{safe_name}_{timestamp}.docx"

    return buffer, filename


def _build_docx(ctx: ExportContext) -> Document:
    """ExportContext로부터 python-docx Document를 생성한다."""
    doc = Document()

    # 기본 스타일 설정
    style = doc.styles["Normal"]
    style.font.name = "맑은 고딕"
    style.font.size = Pt(10)

    # ── 표지 (첫 번째 섹션, 머리말/꼬리말 없음) ──
    _docx_add_cover(doc, ctx)

    # ── 섹션 구분: 표지 이후부터 머리말/꼬리말 적용 ──
    _docx_setup_body_section(doc, ctx.project_name)

    # ── 목차 ──
    _docx_add_toc(doc, ctx)

    # ── 섹션별 본문 ──
    for section in ctx.scaffold.sections:
        stats, check = ctx.section_data.get(
            section.section_key, (None, None)
        )
        _docx_add_section(doc, section, stats, check)

    # ── 부록 ──
    if ctx.options.include_appendix_a:
        _docx_add_appendix_a(doc, ctx)

    if ctx.options.include_appendix_b and ctx.similar_cases:
        _docx_add_appendix_b(doc, ctx)

    if ctx.options.include_appendix_c and ctx.qa_result:
        _docx_add_appendix_c(doc, ctx)

    return doc


def _docx_add_cover(doc: Document, ctx: ExportContext) -> None:
    """표지 페이지."""
    for _ in range(4):
        doc.add_paragraph("")

    # 문서 제목
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("환경영향평가서 초안")
    run.font.size = Pt(28)
    run.bold = True

    doc.add_paragraph("")

    # 사업명
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(ctx.project_name)
    run.font.size = Pt(20)

    doc.add_paragraph("")
    doc.add_paragraph("")

    # 사업 유형
    if ctx.project_type:
        type_para = doc.add_paragraph()
        type_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = type_para.add_run(
            f"사업 유형: {_project_type_korean(ctx.project_type)}"
        )
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(80, 80, 80)

    # 사업 위치 (geometry 중심점 좌표)
    if ctx.centroid:
        loc_para = doc.add_paragraph()
        loc_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        lat, lon = ctx.centroid
        run = loc_para.add_run(f"사업 위치: N {lat:.4f}°, E {lon:.4f}°")
        run.font.size = Pt(12)
        run.font.color.rgb = RGBColor(80, 80, 80)

    doc.add_paragraph("")

    # 작성일
    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_str = ctx.generated_at[:10] if len(ctx.generated_at) >= 10 else ctx.generated_at
    run = date_para.add_run(f"작성일: {date_str}")
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(100, 100, 100)

    # "EIA Draft Copilot으로 작성"
    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info.add_run("EIA Draft Copilot으로 작성")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(150, 150, 150)

    doc.add_page_break()


def _docx_setup_body_section(doc: Document, project_name: str) -> None:
    """본문 섹션의 머리말/꼬리말을 설정한다.

    표지 이후 새 섹션을 추가하고, 머리말에 사업명(좌) + 문서명(우),
    꼬리말에 페이지 번호(중앙)를 배치한다.
    """
    # 새 섹션 생성 (연속이 아닌 새 페이지)
    new_section = doc.add_section()
    new_section.start_type = 2  # WD_SECTION_START.NEW_PAGE

    # ── 머리말 ──
    header = new_section.header
    header.is_linked_to_previous = False

    # 머리말 단락 생성 (탭 정렬: 좌-사업명, 우-문서제목)
    h_para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    h_para.clear()

    # 좌측: 사업명
    run_left = h_para.add_run(project_name)
    run_left.font.size = Pt(8)
    run_left.font.color.rgb = RGBColor(120, 120, 120)

    # 탭 + 우측: 문서 제목
    run_tab = h_para.add_run("\t")
    run_right = h_para.add_run("환경영향평가서 초안")
    run_right.font.size = Pt(8)
    run_right.font.color.rgb = RGBColor(120, 120, 120)

    # 탭 정렬: 우측 탭 위치 설정
    pPr = h_para._p.get_or_add_pPr()
    tabs = parse_xml(
        f'<w:tabs {nsdecls("w")}>'
        f'  <w:tab w:val="right" w:pos="9072"/>'
        f'</w:tabs>'
    )
    pPr.append(tabs)

    # 머리말 하단 구분선
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:bottom w:val="single" w:sz="4" w:space="1" w:color="CCCCCC"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)

    # ── 꼬리말 ──
    footer = new_section.footer
    footer.is_linked_to_previous = False

    f_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    f_para.clear()
    f_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 페이지 번호 필드 삽입
    _docx_add_page_number_field(f_para)

    # 꼬리말 상단 구분선
    f_pPr = f_para._p.get_or_add_pPr()
    f_pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="1" w:color="CCCCCC"/>'
        f'</w:pBdr>'
    )
    f_pPr.append(f_pBdr)

    # 표지 섹션(첫 번째 섹션)의 머리말/꼬리말 비활성화
    first_section = doc.sections[0]
    first_section.header.is_linked_to_previous = False
    first_section.footer.is_linked_to_previous = False
    # 표지 머리말/꼬리말을 비움
    for p in first_section.header.paragraphs:
        p.clear()
    for p in first_section.footer.paragraphs:
        p.clear()


def _docx_add_page_number_field(paragraph) -> None:
    """꼬리말에 페이지 번호 필드를 삽입한다. 형식: '- N -'"""
    _ns = nsdecls("w")
    _font_size = Pt(9)
    _font_color = RGBColor(120, 120, 120)

    # "- " 접두사
    run_prefix = paragraph.add_run("- ")
    run_prefix.font.size = _font_size
    run_prefix.font.color.rgb = _font_color

    # PAGE 필드 — begin / instrText / separate / placeholder / end
    run_begin = paragraph.add_run()
    run_begin.font.size = _font_size
    run_begin.font.color.rgb = _font_color
    run_begin._r.append(parse_xml(f'<w:fldChar {_ns} w:fldCharType="begin"/>'))

    run_instr = paragraph.add_run()
    run_instr.font.size = _font_size
    run_instr.font.color.rgb = _font_color
    run_instr._r.append(parse_xml(f'<w:instrText {_ns} xml:space="preserve"> PAGE </w:instrText>'))

    run_sep = paragraph.add_run()
    run_sep.font.size = _font_size
    run_sep.font.color.rgb = _font_color
    run_sep._r.append(parse_xml(f'<w:fldChar {_ns} w:fldCharType="separate"/>'))

    run_num = paragraph.add_run("1")
    run_num.font.size = _font_size
    run_num.font.color.rgb = _font_color

    run_end = paragraph.add_run()
    run_end.font.size = _font_size
    run_end.font.color.rgb = _font_color
    run_end._r.append(parse_xml(f'<w:fldChar {_ns} w:fldCharType="end"/>'))

    # " -" 접미사
    run_suffix = paragraph.add_run(" -")
    run_suffix.font.size = _font_size
    run_suffix.font.color.rgb = _font_color


def _docx_add_toc(doc: Document, ctx: ExportContext) -> None:
    """목차 페이지."""
    heading = doc.add_heading("목 차", level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph("")

    # 목차 테이블 형태로 구성
    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # 헤더
    headers = ["번호", "섹션명", "상태"]
    for i, h_text in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h_text
        _docx_set_cell_shading(cell, _HEADER_BG)
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            run.bold = True
            run.font.size = Pt(10)

    for section in ctx.scaffold.sections:
        row = table.add_row()
        row.cells[0].text = f"제{section.order}장"
        row.cells[1].text = section.title
        state = _state_label(section.state)
        entry_count = len(section.evidence_entries)
        row.cells[2].text = f"{state} ({entry_count}건)"

        # 상태에 따라 색상 설정
        for cell_idx in range(3):
            para = row.cells[cell_idx].paragraphs[0]
            for run in para.runs:
                run.font.size = Pt(10)

        # 미수집이면 붉은 텍스트
        if section.state == "empty":
            for run in row.cells[2].paragraphs[0].runs:
                run.font.color.rgb = RGBColor(180, 0, 0)

    # 열 너비 설정
    widths = [Cm(3), Cm(9), Cm(4)]
    for row in table.rows:
        for i, width in enumerate(widths):
            row.cells[i].width = width

    # 부록 목차
    if ctx.options.include_appendix_a or ctx.options.include_appendix_b or ctx.options.include_appendix_c:
        doc.add_paragraph("")
        app_heading = doc.add_paragraph()
        run = app_heading.add_run("부록")
        run.bold = True
        run.font.size = Pt(12)

        if ctx.options.include_appendix_a:
            doc.add_paragraph("부록 A: 상세 측정 데이터", style="List Number")
        if ctx.options.include_appendix_b:
            doc.add_paragraph("부록 B: 유사사례 매칭 결과", style="List Number")
        if ctx.options.include_appendix_c:
            doc.add_paragraph("부록 C: QA 검사 결과", style="List Number")

    doc.add_page_break()


def _docx_add_section(
    doc: Document,
    section: ScaffoldSection,
    stats,
    check,
) -> None:
    """개별 섹션을 DOCX에 추가한다. 계층 번호 체계 적용."""
    chapter = section.order

    # 제N장 제목
    doc.add_heading(f"제{chapter}장 {section.title}", level=1)
    desc_para = doc.add_paragraph(section.description)
    desc_para.italic = True

    if not section.evidence_entries:
        para = doc.add_paragraph(
            section.narrative or "데이터가 수집되지 않았습니다."
        )
        if para.runs:
            para.runs[0].font.color.rgb = RGBColor(180, 0, 0)
        doc.add_paragraph("")
        return

    # N.1 현황 및 영향 분석 (서술문)
    doc.add_heading(f"{chapter}.1 현황 및 영향 분석", level=2)
    for line in section.narrative.split("\n"):
        if line.strip():
            doc.add_paragraph(line)

    # N.2 측정 현황 요약 (통계 테이블)
    if stats and stats.indicator_stats:
        indicator_with_data = [s for s in stats.indicator_stats if s.count > 0]
        if indicator_with_data:
            doc.add_heading(f"{chapter}.2 측정 현황 요약", level=2)
            _docx_add_stats_table(doc, indicator_with_data, check)

    # N.3 환경기준 비교 (기준 비교 테이블)
    # standard_value가 정의된 지표를 모두 포함 (NA 상태도 표시)
    if check and check.indicators:
        with_standards = [r for r in check.indicators if r.standard_value is not None]
        if with_standards:
            doc.add_heading(f"{chapter}.3 환경기준 비교", level=2)
            _docx_add_standards_table(doc, with_standards)

    # N.4 측정 데이터 (대표 샘플)
    doc.add_heading(f"{chapter}.4 측정 데이터", level=2)
    sample_entries = section.evidence_entries[:MAX_DETAIL_SAMPLES]
    _docx_add_evidence_table(doc, sample_entries)
    if len(section.evidence_entries) > MAX_DETAIL_SAMPLES:
        remaining = len(section.evidence_entries) - MAX_DETAIL_SAMPLES
        para = doc.add_paragraph(f"※ 외 {remaining}건은 부록 A 참조")
        if para.runs:
            para.runs[0].font.size = Pt(9)
            para.runs[0].font.color.rgb = RGBColor(120, 120, 120)

    doc.add_paragraph("")


def _docx_set_cell_shading(cell, color_hex: str) -> None:
    """DOCX 테이블 셀에 배경색을 설정한다."""
    shading = parse_xml(
        f'<w:shd {nsdecls("w")} w:fill="{color_hex}" w:val="clear"/>'
    )
    cell._tc.get_or_add_tcPr().append(shading)


def _docx_style_header_row(table, col_count: int) -> None:
    """테이블 헤더 행에 배경색, 굵은 글씨, 중앙 정렬, 패딩을 적용한다."""
    for i in range(col_count):
        cell = table.rows[0].cells[i]
        _docx_set_cell_shading(cell, _HEADER_BG)
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            run.bold = True
            run.font.size = Pt(9)


def _docx_style_data_row(row, font_size: int = 9) -> None:
    """데이터 행 폰트 크기 설정."""
    for cell in row.cells:
        for para in cell.paragraphs:
            for run in para.runs:
                run.font.size = Pt(font_size)


def _docx_add_stats_table(doc: Document, indicator_stats, check) -> None:
    """통계 요약 테이블 — 헤더 배경색, 열 너비 조정."""
    check_map = {}
    if check:
        check_map = {r.indicator: r for r in check.indicators}
    has_standards = bool(check_map)

    if has_standards:
        headers = ["지표", "평균", "최대", "최소", "건수", "환경기준", "판정"]
        col_count = 7
    else:
        headers = ["지표", "평균", "최대", "최소", "건수"]
        col_count = 5

    table = doc.add_table(rows=1, cols=col_count)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    # 헤더 설정
    for i, header_text in enumerate(headers):
        table.rows[0].cells[i].text = header_text
    _docx_style_header_row(table, col_count)

    # 데이터 행
    for idx, s in enumerate(indicator_stats):
        unit_suffix = f" {s.unit}" if s.unit else ""
        row = table.add_row()
        row.cells[0].text = s.indicator
        row.cells[1].text = f"{s.mean:.4g}{unit_suffix}" if s.mean is not None else "-"
        row.cells[2].text = f"{s.max_value:.4g}{unit_suffix}" if s.max_value is not None else "-"
        row.cells[3].text = f"{s.min_value:.4g}{unit_suffix}" if s.min_value is not None else "-"
        row.cells[4].text = str(s.count)

        is_exceed = False
        if has_standards:
            cr = check_map.get(s.indicator)
            if cr and cr.standard_value is not None:
                std_unit = cr.standard_unit or ""
                row.cells[5].text = f"{cr.standard_value:.4g} {std_unit}".strip()
                if cr.status == CheckStatus.PASS:
                    row.cells[6].text = "적합"
                elif cr.status == CheckStatus.FAIL:
                    row.cells[6].text = "초과"
                    is_exceed = True
                else:
                    row.cells[6].text = "-"
            else:
                row.cells[5].text = "-"
                row.cells[6].text = "-"

        _docx_style_data_row(row)

        # 초과 시 해당 행 배경색
        if is_exceed:
            for cell in row.cells:
                _docx_set_cell_shading(cell, _EXCEED_BG)
        elif idx % 2 == 1:
            # 교차 행 배경
            for cell in row.cells:
                _docx_set_cell_shading(cell, _ALT_ROW_BG)

    # 열 너비 설정
    if has_standards:
        widths = [Cm(3.5), Cm(2.5), Cm(2.5), Cm(2.5), Cm(1.5), Cm(2.5), Cm(2)]
    else:
        widths = [Cm(4), Cm(3), Cm(3), Cm(3), Cm(2)]
    for row in table.rows:
        for i, width in enumerate(widths):
            row.cells[i].width = width


def _short_legal_ref(legal_basis: str) -> str:
    """법적 근거를 테이블 열에 적합한 간략 형태로 변환한다."""
    if not legal_basis:
        return "-"
    if "환경정책기본법" in legal_basis:
        return "환경정책기본법 별표1"
    if "토양환경보전법" in legal_basis:
        return "토양환경보전법 별표3"
    return legal_basis[:20]


def _docx_add_standards_table(doc: Document, check_results) -> None:
    """환경기준 비교 테이블 — 초과 셀 빨간 배경, 법적 근거 열 포함."""
    headers = ["지표", "시간기준", "환경기준", "측정평균", "판정", "법적 근거"]
    col_count = 6
    table = doc.add_table(rows=1, cols=col_count)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    for i, header_text in enumerate(headers):
        table.rows[0].cells[i].text = header_text
    _docx_style_header_row(table, col_count)

    for idx, cr in enumerate(check_results):
        row = table.add_row()
        row.cells[0].text = cr.indicator
        row.cells[1].text = cr.time_basis or "-"
        std_unit = cr.standard_unit or ""
        row.cells[2].text = (
            f"{cr.standard_value:.4g} {std_unit}".strip()
            if cr.standard_value is not None else "-"
        )
        row.cells[3].text = (
            f"{cr.measured_avg:.4g} {std_unit}".strip()
            if cr.measured_avg is not None else "-"
        )

        is_exceed = False
        if cr.status == CheckStatus.PASS:
            row.cells[4].text = "적합"
        elif cr.status == CheckStatus.FAIL:
            row.cells[4].text = "초과"
            is_exceed = True
        else:
            row.cells[4].text = "-"

        # 법적 근거 열
        row.cells[5].text = _short_legal_ref(
            cr.legal_basis if hasattr(cr, "legal_basis") else ""
        )

        _docx_style_data_row(row)

        # 초과 시 해당 행 배경 연한 빨간색
        if is_exceed:
            for cell in row.cells:
                _docx_set_cell_shading(cell, _EXCEED_BG)
        elif idx % 2 == 1:
            for cell in row.cells:
                _docx_set_cell_shading(cell, _ALT_ROW_BG)

    widths = [Cm(3), Cm(2), Cm(3), Cm(3), Cm(1.5), Cm(3.5)]
    for row in table.rows:
        for i, width in enumerate(widths):
            row.cells[i].width = width


def _docx_add_evidence_table(doc: Document, entries: list[EvidenceEntry]) -> None:
    """근거 데이터 샘플 테이블."""
    if not entries:
        return

    headers = ["지표", "측정값", "단위", "관측일"]
    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    for i, header_text in enumerate(headers):
        table.rows[0].cells[i].text = header_text
    _docx_style_header_row(table, 4)

    for idx, entry in enumerate(entries):
        row = table.add_row()
        row.cells[0].text = entry.indicator
        row.cells[1].text = entry.value
        row.cells[2].text = entry.unit or "-"
        row.cells[3].text = entry.observed_at[:10] if entry.observed_at else "-"
        _docx_style_data_row(row)

        if idx % 2 == 1:
            for cell in row.cells:
                _docx_set_cell_shading(cell, _ALT_ROW_BG)

    widths = [Cm(4), Cm(5), Cm(3), Cm(3)]
    for row in table.rows:
        for i, width in enumerate(widths):
            row.cells[i].width = width


# ── DOCX 부록 ──

def _docx_add_appendix_a(doc: Document, ctx: ExportContext) -> None:
    """부록 A: 상세 측정 데이터 (섹션별 전체 데이터, 최대 50건/섹션)."""
    doc.add_page_break()
    doc.add_heading("부록 A: 상세 측정 데이터", level=1)
    doc.add_paragraph(
        "각 섹션별 수집된 측정 데이터의 상세 목록입니다. "
        f"섹션당 최대 {MAX_APPENDIX_ENTRIES}건까지 표시합니다."
    )

    has_data = False
    for section in ctx.scaffold.sections:
        if not section.evidence_entries:
            continue
        has_data = True

        doc.add_heading(f"A-{section.order}. {section.title}", level=2)

        entries = section.evidence_entries[:MAX_APPENDIX_ENTRIES]

        headers = ["#", "지표", "측정값", "단위", "관측일"]
        table = doc.add_table(rows=1, cols=5)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, h_text in enumerate(headers):
            table.rows[0].cells[i].text = h_text
        _docx_style_header_row(table, 5)

        for idx, entry in enumerate(entries):
            row = table.add_row()
            row.cells[0].text = str(idx + 1)
            row.cells[1].text = entry.indicator
            row.cells[2].text = entry.value
            row.cells[3].text = entry.unit or "-"
            row.cells[4].text = entry.observed_at[:10] if entry.observed_at else "-"
            _docx_style_data_row(row, font_size=8)

            if idx % 2 == 1:
                for cell in row.cells:
                    _docx_set_cell_shading(cell, _ALT_ROW_BG)

        # 열 너비
        widths = [Cm(1.2), Cm(4), Cm(4.5), Cm(2.5), Cm(3)]
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = width

        total = len(section.evidence_entries)
        if total > MAX_APPENDIX_ENTRIES:
            para = doc.add_paragraph(
                f"※ 전체 {total}건 중 {MAX_APPENDIX_ENTRIES}건만 표시"
            )
            if para.runs:
                para.runs[0].font.size = Pt(8)
                para.runs[0].font.color.rgb = RGBColor(120, 120, 120)

        doc.add_paragraph("")

    if not has_data:
        doc.add_paragraph("수집된 측정 데이터가 없습니다.")


def _docx_add_appendix_b(doc: Document, ctx: ExportContext) -> None:
    """부록 B: 유사사례 매칭 결과."""
    doc.add_page_break()
    doc.add_heading("부록 B: 유사사례 매칭 결과", level=1)
    doc.add_paragraph(
        "사업 유형, 위치, 규모, 환경 분야를 기준으로 산출한 유사사례 목록입니다."
    )

    if not ctx.similar_cases:
        doc.add_paragraph("매칭된 유사사례가 없습니다.")
        return

    # 유사사례 테이블
    headers = ["순위", "사례명", "사업유형", "종합점수", "유형", "위치", "규모", "분야"]
    table = doc.add_table(rows=1, cols=8)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, h_text in enumerate(headers):
        table.rows[0].cells[i].text = h_text
    _docx_style_header_row(table, 8)

    for idx, case in enumerate(ctx.similar_cases):
        row = table.add_row()
        row.cells[0].text = str(idx + 1)
        row.cells[1].text = case.name
        row.cells[2].text = _project_type_korean(case.project_type)
        row.cells[3].text = f"{case.overall_score:.2f}"
        row.cells[4].text = f"{case.type_score:.2f}"
        row.cells[5].text = f"{case.location_score:.2f}"
        row.cells[6].text = f"{case.scale_score:.2f}"
        row.cells[7].text = f"{case.category_score:.2f}"
        _docx_style_data_row(row, font_size=8)

        if idx % 2 == 1:
            for cell in row.cells:
                _docx_set_cell_shading(cell, _ALT_ROW_BG)

    widths = [Cm(1.2), Cm(4), Cm(2.5), Cm(2), Cm(1.5), Cm(1.5), Cm(1.5), Cm(1.5)]
    for row in table.rows:
        for i, width in enumerate(widths):
            row.cells[i].width = width

    # 유사사례 상세 요약
    doc.add_paragraph("")
    for idx, case in enumerate(ctx.similar_cases):
        if case.summary:
            doc.add_heading(f"B-{idx + 1}. {case.name}", level=2)
            doc.add_paragraph(case.summary)


def _docx_add_appendix_c(doc: Document, ctx: ExportContext) -> None:
    """부록 C: QA 검사 결과."""
    doc.add_page_break()
    doc.add_heading("부록 C: QA 검사 결과", level=1)

    qa = ctx.qa_result
    if qa is None:
        doc.add_paragraph("QA 검사 결과가 없습니다.")
        return

    # 요약
    summary_para = doc.add_paragraph()
    summary_para.add_run(
        f"검사 시각: {qa.run_at[:19].replace('T', ' ')}  |  "
        f"Critical: {qa.summary.critical_count}건  |  "
        f"Warning: {qa.summary.warning_count}건  |  "
        f"Info: {qa.summary.info_count}건  |  "
        f"Export 가능: {'예' if qa.export_ready else '아니오'}"
    ).font.size = Pt(10)

    doc.add_paragraph("")

    if not qa.issues:
        doc.add_paragraph("검출된 QA 이슈가 없습니다.")
        return

    # 이슈 테이블
    headers = ["#", "심각도", "규칙", "섹션", "제목", "설명"]
    table = doc.add_table(rows=1, cols=6)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    for i, h_text in enumerate(headers):
        table.rows[0].cells[i].text = h_text
    _docx_style_header_row(table, 6)

    for idx, issue in enumerate(qa.issues):
        row = table.add_row()
        row.cells[0].text = str(idx + 1)
        row.cells[1].text = issue.severity.value
        row.cells[2].text = issue.rule_id
        row.cells[3].text = issue.section_key or "-"
        row.cells[4].text = issue.title
        row.cells[5].text = issue.message
        _docx_style_data_row(row, font_size=8)

        # critical 이슈는 빨간 배경
        if issue.severity.value == "critical":
            for cell in row.cells:
                _docx_set_cell_shading(cell, _EXCEED_BG)
        elif idx % 2 == 1:
            for cell in row.cells:
                _docx_set_cell_shading(cell, _ALT_ROW_BG)

    widths = [Cm(1), Cm(1.8), Cm(1.5), Cm(2.5), Cm(4), Cm(5)]
    for row in table.rows:
        for i, width in enumerate(widths):
            row.cells[i].width = width


# ═══════════════════════════════════════════════════════════════
# PDF 출력 (reportlab)
# ═══════════════════════════════════════════════════════════════

def _register_korean_font() -> str:
    """한글 폰트를 등록하고 폰트 이름을 반환한다."""
    registered = pdfmetrics.getRegisteredFontNames()

    for font_path in [
        "C:/Windows/Fonts/malgun.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/nanum/NanumGothic.ttf",
    ]:
        if os.path.exists(font_path):
            font_name = "MalgunGothic" if "malgun" in font_path else "NanumGothic"
            if font_name not in registered:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
            return font_name

    cid_name = "HYGothic-Medium"
    if cid_name not in registered:
        pdfmetrics.registerFont(UnicodeCIDFont(cid_name))
    return cid_name


def _get_pdf_styles(font_name: str) -> dict[str, ParagraphStyle]:
    """PDF용 스타일 사전을 생성한다."""
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "KoTitle", parent=base["Title"],
            fontName=font_name, fontSize=28, leading=34,
            alignment=1, spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "KoSubtitle", parent=base["Normal"],
            fontName=font_name, fontSize=20, leading=26,
            alignment=1, spaceAfter=8,
        ),
        "heading1": ParagraphStyle(
            "KoH1", parent=base["Heading1"],
            fontName=font_name, fontSize=16, leading=22,
            spaceBefore=20, spaceAfter=10,
        ),
        "heading2": ParagraphStyle(
            "KoH2", parent=base["Heading2"],
            fontName=font_name, fontSize=13, leading=18,
            spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "KoBody", parent=base["Normal"],
            fontName=font_name, fontSize=10, leading=15,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "KoSmall", parent=base["Normal"],
            fontName=font_name, fontSize=8, leading=12,
        ),
        "center": ParagraphStyle(
            "KoCenter", parent=base["Normal"],
            fontName=font_name, fontSize=12, leading=16,
            alignment=1,
        ),
        "center_gray": ParagraphStyle(
            "KoCenterGray", parent=base["Normal"],
            fontName=font_name, fontSize=10, leading=15,
            alignment=1, textColor=colors.Color(0.6, 0.6, 0.6),
        ),
        "center_info": ParagraphStyle(
            "KoCenterInfo", parent=base["Normal"],
            fontName=font_name, fontSize=12, leading=16,
            alignment=1, textColor=colors.Color(0.3, 0.3, 0.3),
        ),
        "italic_desc": ParagraphStyle(
            "KoItalicDesc", parent=base["Normal"],
            fontName=font_name, fontSize=10, leading=14,
            textColor=colors.Color(0.3, 0.3, 0.3), spaceAfter=8,
        ),
        "no_data": ParagraphStyle(
            "KoNoData", parent=base["Normal"],
            fontName=font_name, fontSize=10, leading=14,
            textColor=colors.Color(0.7, 0, 0),
        ),
        "note": ParagraphStyle(
            "KoNote", parent=base["Normal"],
            fontName=font_name, fontSize=9, leading=13,
            textColor=colors.Color(0.5, 0.5, 0.5),
        ),
        "appendix_h1": ParagraphStyle(
            "KoAppH1", parent=base["Heading1"],
            fontName=font_name, fontSize=16, leading=22,
            spaceBefore=12, spaceAfter=8,
        ),
        "appendix_h2": ParagraphStyle(
            "KoAppH2", parent=base["Heading2"],
            fontName=font_name, fontSize=12, leading=16,
            spaceBefore=10, spaceAfter=4,
        ),
    }


# PDF 테이블 스타일 (헤더 연한 파란, 교차 행)
_PDF_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.84, 0.89, 0.94)),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.Color(0.1, 0.1, 0.1)),
    ("FONTSIZE", (0, 0), (-1, 0), 9),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
     [colors.white, colors.Color(0.96, 0.96, 0.97)]),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
])

# PDF 초과 행 스타일 (빨간 배경)
_PDF_EXCEED_BG = colors.Color(0.99, 0.88, 0.86)


async def generate_pdf(
    db: AsyncSession,
    project: Project,
    *,
    options: ExportOptions | None = None,
    skip_qa_check: bool = False,
) -> tuple[io.BytesIO, str]:
    """PDF 문서를 생성하여 BytesIO와 파일명을 반환한다."""
    qa_result = None
    if not skip_qa_check:
        qa_result = await run_qa(db, project.id)
        if not qa_result.export_ready:
            raise ValueError(
                f"critical 이슈 {qa_result.summary.critical_count}건이 "
                f"남아 있어 export가 차단되었습니다."
            )

    ctx = await _build_export_context(
        db, project,
        options=options,
        qa_result=qa_result,
    )

    buffer = _build_pdf(ctx)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(
        c if c.isascii() and c.isalnum() or c in "-_" else "_"
        for c in project.name.replace(" ", "_")
    )[:50].strip("_") or "draft"
    filename = f"EIA_{safe_name}_{timestamp}.pdf"

    return buffer, filename


def _pdf_header_footer(canvas, doc_template, project_name: str):
    """PDF 페이지 머리말/꼬리말 (첫 페이지 제외)."""
    canvas.saveState()
    page_num = canvas.getPageNumber()

    # 첫 페이지(표지)는 머리말/꼬리말 생략
    if page_num <= 1:
        canvas.restoreState()
        return

    width, height = A4

    # 머리말
    canvas.setFont(doc_template._pdf_font_name, 8)
    canvas.setFillColor(colors.Color(0.5, 0.5, 0.5))
    canvas.drawString(2 * cm, height - 1.3 * cm, project_name)
    canvas.drawRightString(width - 2 * cm, height - 1.3 * cm, "환경영향평가서 초안")
    # 머리말 구분선
    canvas.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
    canvas.line(2 * cm, height - 1.5 * cm, width - 2 * cm, height - 1.5 * cm)

    # 꼬리말
    canvas.setFont(doc_template._pdf_font_name, 9)
    canvas.setFillColor(colors.Color(0.5, 0.5, 0.5))
    canvas.drawCentredString(width / 2, 1.3 * cm, f"- {page_num} -")
    # 꼬리말 구분선
    canvas.line(2 * cm, 1.6 * cm, width - 2 * cm, 1.6 * cm)

    canvas.restoreState()


def _build_pdf(ctx: ExportContext) -> io.BytesIO:
    """ExportContext로부터 reportlab PDF 문서를 생성한다."""
    font_name = _register_korean_font()
    styles = _get_pdf_styles(font_name)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title=f"환경영향평가서 초안 — {ctx.project_name}",
        author="EIA Draft Copilot",
    )

    # 커스텀 속성에 폰트 이름 저장 (header/footer에서 사용)
    doc._pdf_font_name = font_name
    doc._pdf_project_name = ctx.project_name

    story: list = []

    # 표지
    _pdf_add_cover(story, styles, ctx)

    # 목차
    _pdf_add_toc(story, styles, font_name, ctx)

    # 본문 섹션
    for section in ctx.scaffold.sections:
        stats, check = ctx.section_data.get(
            section.section_key, (None, None)
        )
        _pdf_add_section(story, styles, font_name, section, stats, check)

    # 부록
    if ctx.options.include_appendix_a:
        _pdf_add_appendix_a(story, styles, font_name, ctx)

    if ctx.options.include_appendix_b and ctx.similar_cases:
        _pdf_add_appendix_b(story, styles, font_name, ctx)

    if ctx.options.include_appendix_c and ctx.qa_result:
        _pdf_add_appendix_c(story, styles, font_name, ctx)

    # 머리말/꼬리말 콜백
    def on_page(canvas, doc_t):
        _pdf_header_footer(canvas, doc_t, ctx.project_name)

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    buffer.seek(0)
    return buffer


def _pdf_add_cover(story, styles, ctx: ExportContext):
    """PDF 표지 페이지."""
    story.append(Spacer(1, 5 * cm))
    story.append(Paragraph("환경영향평가서 초안", styles["title"]))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(ctx.project_name, styles["subtitle"]))
    story.append(Spacer(1, 1.5 * cm))

    # 사업 유형
    if ctx.project_type:
        story.append(Paragraph(
            f"사업 유형: {_project_type_korean(ctx.project_type)}",
            styles["center_info"],
        ))

    # 사업 위치
    if ctx.centroid:
        lat, lon = ctx.centroid
        story.append(Paragraph(
            f"사업 위치: N {lat:.4f}°, E {lon:.4f}°",
            styles["center_info"],
        ))

    story.append(Spacer(1, 1 * cm))

    date_str = ctx.generated_at[:10] if len(ctx.generated_at) >= 10 else ctx.generated_at
    story.append(Paragraph(f"작성일: {date_str}", styles["center"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("EIA Draft Copilot으로 작성", styles["center_gray"]))
    story.append(PageBreak())


def _pdf_add_toc(story, styles, font_name, ctx: ExportContext):
    """PDF 목차 페이지."""
    story.append(Paragraph("목 차", styles["heading1"]))
    story.append(Spacer(1, 0.5 * cm))

    # 목차 테이블
    header_s = _make_header_style(font_name)
    cell_s = _make_cell_style(font_name, size=10)

    data = [[
        Paragraph("번호", header_s),
        Paragraph("섹션명", header_s),
        Paragraph("상태", header_s),
    ]]

    for section in ctx.scaffold.sections:
        state = _state_label(section.state)
        entry_count = len(section.evidence_entries)
        state_text = f"{state} ({entry_count}건)"

        data.append([
            Paragraph(f"제{section.order}장", cell_s),
            Paragraph(section.title, cell_s),
            Paragraph(state_text, cell_s),
        ])

    col_widths = [2.5 * cm, 8 * cm, 4 * cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_PDF_TABLE_STYLE)
    story.append(table)

    # 부록 목차
    if ctx.options.include_appendix_a or ctx.options.include_appendix_b or ctx.options.include_appendix_c:
        story.append(Spacer(1, 0.8 * cm))
        story.append(Paragraph("<b>부록</b>", styles["body"]))
        if ctx.options.include_appendix_a:
            story.append(Paragraph("부록 A: 상세 측정 데이터", styles["body"]))
        if ctx.options.include_appendix_b:
            story.append(Paragraph("부록 B: 유사사례 매칭 결과", styles["body"]))
        if ctx.options.include_appendix_c:
            story.append(Paragraph("부록 C: QA 검사 결과", styles["body"]))

    story.append(PageBreak())


def _pdf_add_section(story, styles, font_name, section, stats, check):
    """개별 섹션을 PDF에 추가한다. 계층 번호 체계."""
    chapter = section.order

    story.append(Paragraph(f"제{chapter}장 {section.title}", styles["heading1"]))
    story.append(Paragraph(section.description, styles["italic_desc"]))

    if not section.evidence_entries:
        story.append(Paragraph(
            section.narrative or "데이터가 수집되지 않았습니다.",
            styles["no_data"],
        ))
        story.append(Spacer(1, 0.5 * cm))
        return

    # N.1 현황 및 영향 분석
    story.append(Paragraph(f"{chapter}.1 현황 및 영향 분석", styles["heading2"]))
    for line in section.narrative.split("\n"):
        if line.strip():
            story.append(Paragraph(line, styles["body"]))

    # N.2 측정 현황 요약
    if stats and stats.indicator_stats:
        indicator_with_data = [s for s in stats.indicator_stats if s.count > 0]
        if indicator_with_data:
            story.append(Paragraph(f"{chapter}.2 측정 현황 요약", styles["heading2"]))
            _pdf_add_stats_table(story, font_name, indicator_with_data, check)

    # N.3 환경기준 비교
    # standard_value가 정의된 지표를 모두 포함 (NA 상태도 표시)
    if check and check.indicators:
        with_standards = [r for r in check.indicators if r.standard_value is not None]
        if with_standards:
            story.append(Paragraph(f"{chapter}.3 환경기준 비교", styles["heading2"]))
            _pdf_add_standards_table(story, font_name, with_standards)

    # N.4 측정 데이터
    story.append(Paragraph(f"{chapter}.4 측정 데이터", styles["heading2"]))
    sample_entries = section.evidence_entries[:MAX_DETAIL_SAMPLES]
    _pdf_add_evidence_table(story, font_name, sample_entries)
    if len(section.evidence_entries) > MAX_DETAIL_SAMPLES:
        remaining = len(section.evidence_entries) - MAX_DETAIL_SAMPLES
        story.append(Paragraph(
            f"※ 외 {remaining}건은 부록 A 참조",
            styles["note"],
        ))
    story.append(Spacer(1, 0.5 * cm))


def _make_cell_style(font_name: str, size: int = 8, alignment: int = 0) -> ParagraphStyle:
    """PDF 테이블 셀 스타일."""
    return ParagraphStyle(
        f"Cell{size}_{alignment}_{id(font_name)}",
        fontName=font_name, fontSize=size, leading=size + 3,
        alignment=alignment,
    )


def _make_header_style(font_name: str) -> ParagraphStyle:
    """PDF 테이블 헤더 스타일."""
    return ParagraphStyle(
        f"TblHeader_{id(font_name)}",
        fontName=font_name, fontSize=9, leading=12,
        alignment=1,
    )


def _pdf_add_stats_table(story, font_name, indicator_stats, check):
    """통계 요약 테이블 — PDF."""
    header_s = _make_header_style(font_name)
    cell_s = _make_cell_style(font_name)

    check_map = {}
    if check:
        check_map = {r.indicator: r for r in check.indicators}
    has_standards = bool(check_map)

    if has_standards:
        data = [[
            Paragraph("지표", header_s), Paragraph("평균", header_s),
            Paragraph("최대", header_s), Paragraph("최소", header_s),
            Paragraph("건수", header_s), Paragraph("환경기준", header_s),
            Paragraph("판정", header_s),
        ]]
        col_widths = [3 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 1.5 * cm, 2.5 * cm, 2 * cm]
    else:
        data = [[
            Paragraph("지표", header_s), Paragraph("평균", header_s),
            Paragraph("최대", header_s), Paragraph("최소", header_s),
            Paragraph("건수", header_s),
        ]]
        col_widths = [4 * cm, 3 * cm, 3 * cm, 3 * cm, 2 * cm]

    exceed_rows = []
    for row_idx, s in enumerate(indicator_stats):
        unit_suffix = f" {s.unit}" if s.unit else ""
        row = [
            Paragraph(s.indicator, cell_s),
            Paragraph(f"{s.mean:.4g}{unit_suffix}" if s.mean is not None else "-", cell_s),
            Paragraph(f"{s.max_value:.4g}{unit_suffix}" if s.max_value is not None else "-", cell_s),
            Paragraph(f"{s.min_value:.4g}{unit_suffix}" if s.min_value is not None else "-", cell_s),
            Paragraph(str(s.count), cell_s),
        ]
        if has_standards:
            cr = check_map.get(s.indicator)
            if cr and cr.standard_value is not None:
                std_unit = cr.standard_unit or ""
                row.append(Paragraph(f"{cr.standard_value:.4g} {std_unit}".strip(), cell_s))
                status = "적합" if cr.status == CheckStatus.PASS else (
                    "초과" if cr.status == CheckStatus.FAIL else "-")
                row.append(Paragraph(status, cell_s))
                if cr.status == CheckStatus.FAIL:
                    exceed_rows.append(row_idx + 1)  # +1 for header
            else:
                row.extend([Paragraph("-", cell_s), Paragraph("-", cell_s)])
        data.append(row)

    table = Table(data, colWidths=col_widths, repeatRows=1)

    # 기본 스타일 적용
    style_commands = list(_PDF_TABLE_STYLE.getCommands())

    # 초과 행 빨간 배경 추가
    for r in exceed_rows:
        style_commands.append(
            ("BACKGROUND", (0, r), (-1, r), _PDF_EXCEED_BG)
        )

    table.setStyle(TableStyle(style_commands))
    story.append(table)


def _pdf_add_standards_table(story, font_name, check_results):
    """환경기준 비교 테이블 — PDF. 법적 근거 열 포함."""
    header_s = _make_header_style(font_name)
    cell_s = _make_cell_style(font_name)

    data = [[
        Paragraph("지표", header_s), Paragraph("시간기준", header_s),
        Paragraph("환경기준", header_s), Paragraph("측정평균", header_s),
        Paragraph("판정", header_s), Paragraph("법적 근거", header_s),
    ]]

    exceed_rows = []
    for row_idx, cr in enumerate(check_results):
        std_unit = cr.standard_unit or ""
        std_str = f"{cr.standard_value:.4g} {std_unit}".strip() if cr.standard_value is not None else "-"
        avg_str = f"{cr.measured_avg:.4g} {std_unit}".strip() if cr.measured_avg is not None else "-"

        if cr.status == CheckStatus.PASS:
            status = "적합"
        elif cr.status == CheckStatus.FAIL:
            status = "초과"
            exceed_rows.append(row_idx + 1)
        else:
            status = "-"

        legal_short = _short_legal_ref(
            cr.legal_basis if hasattr(cr, "legal_basis") else ""
        )

        data.append([
            Paragraph(cr.indicator, cell_s),
            Paragraph(cr.time_basis or "-", cell_s),
            Paragraph(std_str, cell_s),
            Paragraph(avg_str, cell_s),
            Paragraph(status, cell_s),
            Paragraph(legal_short, cell_s),
        ])

    col_widths = [3 * cm, 2 * cm, 2.5 * cm, 2.5 * cm, 1.5 * cm, 3.5 * cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style_commands = list(_PDF_TABLE_STYLE.getCommands())
    for r in exceed_rows:
        style_commands.append(
            ("BACKGROUND", (0, r), (-1, r), _PDF_EXCEED_BG)
        )
    table.setStyle(TableStyle(style_commands))
    story.append(table)


def _pdf_add_evidence_table(story, font_name, entries):
    """근거 데이터 샘플 테이블 — PDF."""
    if not entries:
        return

    header_s = _make_header_style(font_name)
    cell_s = _make_cell_style(font_name)

    data = [[
        Paragraph("지표", header_s), Paragraph("측정값", header_s),
        Paragraph("단위", header_s), Paragraph("관측일", header_s),
    ]]

    for entry in entries:
        observed = entry.observed_at[:10] if entry.observed_at else "-"
        data.append([
            Paragraph(entry.indicator, cell_s),
            Paragraph(entry.value, cell_s),
            Paragraph(entry.unit or "-", cell_s),
            Paragraph(observed, cell_s),
        ])

    col_widths = [5 * cm, 5 * cm, 3.5 * cm, 3.5 * cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_PDF_TABLE_STYLE)
    story.append(table)


# ── PDF 부록 ──

def _pdf_add_appendix_a(story, styles, font_name, ctx: ExportContext):
    """부록 A: 상세 측정 데이터 — PDF."""
    story.append(PageBreak())
    story.append(Paragraph("부록 A: 상세 측정 데이터", styles["appendix_h1"]))
    story.append(Paragraph(
        f"각 섹션별 수집된 측정 데이터의 상세 목록입니다. "
        f"섹션당 최대 {MAX_APPENDIX_ENTRIES}건까지 표시합니다.",
        styles["body"],
    ))

    header_s = _make_header_style(font_name)
    cell_s = _make_cell_style(font_name, size=7)

    has_data = False
    for section in ctx.scaffold.sections:
        if not section.evidence_entries:
            continue
        has_data = True

        story.append(Paragraph(
            f"A-{section.order}. {section.title}", styles["appendix_h2"]
        ))

        entries = section.evidence_entries[:MAX_APPENDIX_ENTRIES]
        data = [[
            Paragraph("#", header_s),
            Paragraph("지표", header_s),
            Paragraph("측정값", header_s),
            Paragraph("단위", header_s),
            Paragraph("관측일", header_s),
        ]]

        for idx, entry in enumerate(entries):
            observed = entry.observed_at[:10] if entry.observed_at else "-"
            data.append([
                Paragraph(str(idx + 1), cell_s),
                Paragraph(entry.indicator, cell_s),
                Paragraph(entry.value, cell_s),
                Paragraph(entry.unit or "-", cell_s),
                Paragraph(observed, cell_s),
            ])

        col_widths = [1 * cm, 4 * cm, 5 * cm, 3 * cm, 3.5 * cm]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(_PDF_TABLE_STYLE)
        story.append(table)

        total = len(section.evidence_entries)
        if total > MAX_APPENDIX_ENTRIES:
            story.append(Paragraph(
                f"※ 전체 {total}건 중 {MAX_APPENDIX_ENTRIES}건만 표시",
                styles["note"],
            ))

        story.append(Spacer(1, 0.3 * cm))

    if not has_data:
        story.append(Paragraph("수집된 측정 데이터가 없습니다.", styles["body"]))


def _pdf_add_appendix_b(story, styles, font_name, ctx: ExportContext):
    """부록 B: 유사사례 매칭 결과 — PDF."""
    story.append(PageBreak())
    story.append(Paragraph("부록 B: 유사사례 매칭 결과", styles["appendix_h1"]))
    story.append(Paragraph(
        "사업 유형, 위치, 규모, 환경 분야를 기준으로 산출한 유사사례 목록입니다.",
        styles["body"],
    ))

    if not ctx.similar_cases:
        story.append(Paragraph("매칭된 유사사례가 없습니다.", styles["body"]))
        return

    header_s = _make_header_style(font_name)
    cell_s = _make_cell_style(font_name, size=7)

    data = [[
        Paragraph("순위", header_s),
        Paragraph("사례명", header_s),
        Paragraph("사업유형", header_s),
        Paragraph("종합", header_s),
        Paragraph("유형", header_s),
        Paragraph("위치", header_s),
        Paragraph("규모", header_s),
        Paragraph("분야", header_s),
    ]]

    for idx, case in enumerate(ctx.similar_cases):
        data.append([
            Paragraph(str(idx + 1), cell_s),
            Paragraph(case.name, cell_s),
            Paragraph(_project_type_korean(case.project_type), cell_s),
            Paragraph(f"{case.overall_score:.2f}", cell_s),
            Paragraph(f"{case.type_score:.2f}", cell_s),
            Paragraph(f"{case.location_score:.2f}", cell_s),
            Paragraph(f"{case.scale_score:.2f}", cell_s),
            Paragraph(f"{case.category_score:.2f}", cell_s),
        ])

    col_widths = [1 * cm, 4 * cm, 2 * cm, 1.8 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm, 1.5 * cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_PDF_TABLE_STYLE)
    story.append(table)

    # 유사사례 상세 요약
    story.append(Spacer(1, 0.5 * cm))
    for idx, case in enumerate(ctx.similar_cases):
        if case.summary:
            story.append(Paragraph(
                f"B-{idx + 1}. {case.name}", styles["appendix_h2"]
            ))
            story.append(Paragraph(case.summary, styles["body"]))


def _pdf_add_appendix_c(story, styles, font_name, ctx: ExportContext):
    """부록 C: QA 검사 결과 — PDF."""
    story.append(PageBreak())
    story.append(Paragraph("부록 C: QA 검사 결과", styles["appendix_h1"]))

    qa = ctx.qa_result
    if qa is None:
        story.append(Paragraph("QA 검사 결과가 없습니다.", styles["body"]))
        return

    # 요약
    story.append(Paragraph(
        f"검사 시각: {qa.run_at[:19].replace('T', ' ')}  |  "
        f"Critical: {qa.summary.critical_count}건  |  "
        f"Warning: {qa.summary.warning_count}건  |  "
        f"Info: {qa.summary.info_count}건  |  "
        f"Export 가능: {'예' if qa.export_ready else '아니오'}",
        styles["body"],
    ))

    story.append(Spacer(1, 0.3 * cm))

    if not qa.issues:
        story.append(Paragraph("검출된 QA 이슈가 없습니다.", styles["body"]))
        return

    header_s = _make_header_style(font_name)
    cell_s = _make_cell_style(font_name, size=7)

    data = [[
        Paragraph("#", header_s),
        Paragraph("심각도", header_s),
        Paragraph("규칙", header_s),
        Paragraph("섹션", header_s),
        Paragraph("제목", header_s),
    ]]

    critical_rows = []
    for idx, issue in enumerate(qa.issues):
        data.append([
            Paragraph(str(idx + 1), cell_s),
            Paragraph(issue.severity.value, cell_s),
            Paragraph(issue.rule_id, cell_s),
            Paragraph(issue.section_key or "-", cell_s),
            Paragraph(issue.title, cell_s),
        ])
        if issue.severity.value == "critical":
            critical_rows.append(idx + 1)

    col_widths = [1 * cm, 2 * cm, 1.5 * cm, 3 * cm, 8 * cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)

    style_commands = list(_PDF_TABLE_STYLE.getCommands())
    for r in critical_rows:
        style_commands.append(
            ("BACKGROUND", (0, r), (-1, r), _PDF_EXCEED_BG)
        )
    table.setStyle(TableStyle(style_commands))
    story.append(table)


# ═══════════════════════════════════════════════════════════════
# 미리보기 데이터 생성 (프론트엔드용)
# ═══════════════════════════════════════════════════════════════

@dataclass
class PreviewSection:
    """문서 구조 미리보기의 섹션 정보."""

    title: str
    state: str
    evidence_count: int
    has_stats: bool
    has_standards: bool


@dataclass
class ExportPreview:
    """문서 구조 미리보기 전체 정보."""

    project_name: str
    project_type: str | None
    centroid: tuple[float, float] | None
    sections: list[PreviewSection]
    total_evidence: int
    similar_case_count: int
    qa_issue_count: int
    export_ready: bool


async def generate_export_preview(
    db: AsyncSession,
    project: Project,
) -> ExportPreview:
    """Export 전 문서 구조 미리보기 데이터를 생성한다."""
    scaffold = await generate_draft_scaffold(db, project.id)

    sections: list[PreviewSection] = []
    for section in scaffold.sections:
        stats = await calculate_section_statistics(
            db, project.id, section.section_key
        )
        check = await check_section_standards(
            db, project.id, section.section_key
        )
        has_stats = bool(
            stats and stats.indicator_stats
            and any(s.count > 0 for s in stats.indicator_stats)
        )
        has_standards = bool(
            check and check.indicators
            and any(r.status != CheckStatus.NA for r in check.indicators)
        )
        sections.append(PreviewSection(
            title=f"제{section.order}장 {section.title}",
            state=_state_label(section.state),
            evidence_count=len(section.evidence_entries),
            has_stats=has_stats,
            has_standards=has_standards,
        ))

    # 유사사례 수 (중복 제거)
    similar_count = 0
    try:
        from app.services.similarity import find_similar_cases
        categories = {
            s.section_key for s in scaffold.sections if s.evidence_entries
        }
        match_result = await find_similar_cases(
            db, project.id,
            evidence_categories=categories,
            top_k=10,
        )
        unique_names = {m.similar_case.name for m in match_result.matches}
        similar_count = len(unique_names)
    except Exception:
        pass

    # QA
    qa_result = await run_qa(db, project.id)

    return ExportPreview(
        project_name=project.name,
        project_type=project.project_type,
        centroid=_get_centroid_coords(project.geometry),
        sections=sections,
        total_evidence=scaffold.total_evidence_count,
        similar_case_count=similar_count,
        qa_issue_count=qa_result.summary.total,
        export_ready=qa_result.export_ready,
    )
