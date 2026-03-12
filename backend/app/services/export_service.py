"""DOCX/PDF 출력 서비스.

초안 뼈대(DraftScaffold) 데이터를 기반으로 DOCX 및 PDF 문서를 생성한다.
- DOCX: python-docx 사용
- PDF: reportlab 사용 (한글 폰트 지원)

Post-3 개편: 4부 구조 (서술문 → 통계 테이블 → 기준 비교 테이블 → 상세 샘플)
"""

from __future__ import annotations

import io
import os
import uuid
from datetime import datetime, timezone

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
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

from app.services.draft_scaffold import (
    DraftScaffold,
    EvidenceEntry,
    ScaffoldSection,
    generate_draft_scaffold,
    MAX_DETAIL_SAMPLES,
)
from app.services.qa_engine import run_qa
from app.services.standard_checker import (
    CheckStatus,
    check_section_standards,
)
from app.services.statistics import calculate_section_statistics


async def generate_docx(
    db: AsyncSession,
    project_id: uuid.UUID,
    project_name: str,
    *,
    skip_qa_check: bool = False,
) -> tuple[io.BytesIO, str]:
    """DOCX 문서를 생성하여 BytesIO와 파일명을 반환한다.

    Args:
        db: DB 세션
        project_id: 프로젝트 ID
        project_name: 프로젝트 이름 (표지 · 파일명에 사용)
        skip_qa_check: True면 QA 검사를 건너뜀 (테스트용)

    Returns:
        (BytesIO 버퍼, 파일명) 튜플

    Raises:
        ValueError: critical QA 이슈가 있어 export가 차단된 경우
    """
    # Export Gate: QA 검사
    if not skip_qa_check:
        qa_result = await run_qa(db, project_id)
        if not qa_result.export_ready:
            raise ValueError(
                f"critical 이슈 {qa_result.summary.critical_count}건이 "
                f"남아 있어 export가 차단되었습니다."
            )

    # 초안 뼈대 생성
    scaffold = await generate_draft_scaffold(db, project_id)

    # 섹션별 통계/기준비교 데이터 수집 (DOCX 테이블 생성용)
    section_data = {}
    for section in scaffold.sections:
        stats = await calculate_section_statistics(
            db, project_id, section.section_key
        )
        check = await check_section_standards(
            db, project_id, section.section_key
        )
        section_data[section.section_key] = (stats, check)

    # DOCX 문서 생성
    doc = _build_docx(scaffold, project_name, section_data)

    # BytesIO로 직렬화
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # 파일명 생성 (HTTP 헤더 latin-1 호환을 위해 ASCII 안전 처리)
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(
        c if c.isascii() and c.isalnum() or c in "-_" else "_"
        for c in project_name.replace(" ", "_")
    )[:50].strip("_") or "draft"
    filename = f"EIA_{safe_name}_{timestamp}.docx"

    return buffer, filename


def _build_docx(
    scaffold: DraftScaffold,
    project_name: str,
    section_data: dict,
) -> Document:
    """DraftScaffold로부터 python-docx Document를 생성한다."""
    doc = Document()

    # 기본 스타일 설정
    style = doc.styles["Normal"]
    style.font.name = "맑은 고딕"
    style.font.size = Pt(10)

    # ── 표지 ──
    _add_cover_page(doc, project_name, scaffold.generated_at)

    # ── 목차 페이지 ──
    _add_toc_page(doc, scaffold)

    # ── 섹션별 내용 ──
    for section in scaffold.sections:
        stats, check = section_data.get(section.section_key, (None, None))
        _add_section(doc, section, stats, check)

    return doc


def _add_cover_page(doc: Document, project_name: str, generated_at: str) -> None:
    """표지 페이지를 추가한다."""
    for _ in range(6):
        doc.add_paragraph("")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("환경영향평가서")
    run.font.size = Pt(28)
    run.bold = True

    doc.add_paragraph("")

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(project_name)
    run.font.size = Pt(18)

    doc.add_paragraph("")
    doc.add_paragraph("")

    date_para = doc.add_paragraph()
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_str = generated_at[:10] if len(generated_at) >= 10 else generated_at
    run = date_para.add_run(f"생성일: {date_str}")
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(100, 100, 100)

    info = doc.add_paragraph()
    info.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = info.add_run("EIA Draft Copilot에 의해 자동 생성됨")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(150, 150, 150)

    doc.add_page_break()


def _add_toc_page(doc: Document, scaffold: DraftScaffold) -> None:
    """목차 페이지를 추가한다."""
    heading = doc.add_heading("목 차", level=1)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph("")

    for section in scaffold.sections:
        entry_count = len(section.evidence_entries)
        status = "근거 있음" if entry_count > 0 else "미수집"
        para = doc.add_paragraph(
            f"{section.order}. {section.title} — {status} ({entry_count}건)"
        )
        para.style = doc.styles["List Number"]

    doc.add_page_break()


def _add_section(doc: Document, section: ScaffoldSection, stats, check) -> None:
    """개별 섹션을 DOCX에 추가한다. 4부 구조로 출력."""
    doc.add_heading(f"{section.order}. {section.title}", level=1)
    doc.add_paragraph(section.description).italic = True

    if not section.evidence_entries:
        para = doc.add_paragraph(section.narrative or "데이터가 수집되지 않았습니다.")
        para.runs[0].font.color.rgb = RGBColor(180, 0, 0)
        doc.add_paragraph("")
        return

    # 가. 현황 및 영향 분석 (서술문)
    doc.add_heading("가. 현황 및 영향 분석", level=2)
    for line in section.narrative.split("\n"):
        if line.strip():
            doc.add_paragraph(line)

    # 나. 측정 현황 요약 (통계 테이블)
    if stats and stats.indicator_stats:
        indicator_with_data = [s for s in stats.indicator_stats if s.count > 0]
        if indicator_with_data:
            doc.add_heading("나. 측정 현황 요약", level=2)
            _add_stats_table(doc, indicator_with_data, check)

    # 다. 환경기준 비교 (기준 비교 테이블)
    if check and check.indicators:
        measured = [r for r in check.indicators if r.status != CheckStatus.NA]
        if measured:
            doc.add_heading("다. 환경기준 비교", level=2)
            _add_standards_table(doc, measured)

    # 라. 측정 데이터 (대표 샘플 5건)
    doc.add_heading("라. 측정 데이터", level=2)
    sample_entries = section.evidence_entries[:MAX_DETAIL_SAMPLES]
    _add_evidence_table(doc, sample_entries)
    if len(section.evidence_entries) > MAX_DETAIL_SAMPLES:
        remaining = len(section.evidence_entries) - MAX_DETAIL_SAMPLES
        para = doc.add_paragraph(f"※ 외 {remaining}건은 별첨 참조")
        para.runs[0].font.size = Pt(9)
        para.runs[0].font.color.rgb = RGBColor(120, 120, 120)

    doc.add_paragraph("")


def _add_stats_table(doc: Document, indicator_stats, check) -> None:
    """통계 요약 테이블을 DOCX에 추가한다."""
    # 환경기준 비교 결과 매핑
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

    # 헤더
    for i, header_text in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header_text
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            run.bold = True
            run.font.size = Pt(9)

    # 데이터 행
    for s in indicator_stats:
        unit_suffix = f" {s.unit}" if s.unit else ""
        row = table.add_row()
        row.cells[0].text = s.indicator
        row.cells[1].text = f"{s.mean:.4g}{unit_suffix}" if s.mean is not None else "-"
        row.cells[2].text = f"{s.max_value:.4g}{unit_suffix}" if s.max_value is not None else "-"
        row.cells[3].text = f"{s.min_value:.4g}{unit_suffix}" if s.min_value is not None else "-"
        row.cells[4].text = str(s.count)

        if has_standards:
            cr = check_map.get(s.indicator)
            if cr and cr.standard_value is not None:
                std_unit = cr.standard_unit or ""
                row.cells[5].text = f"{cr.standard_value:.4g} {std_unit}".strip()
                row.cells[6].text = (
                    "적합" if cr.status == CheckStatus.PASS else
                    "초과" if cr.status == CheckStatus.FAIL else "-"
                )
            else:
                row.cells[5].text = "-"
                row.cells[6].text = "-"

        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(9)


def _add_standards_table(doc: Document, check_results) -> None:
    """환경기준 비교 테이블을 DOCX에 추가한다."""
    headers = ["지표", "시간기준", "환경기준", "측정평균", "판정"]
    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    for i, header_text in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header_text
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            run.bold = True
            run.font.size = Pt(9)

    for cr in check_results:
        row = table.add_row()
        row.cells[0].text = cr.indicator
        row.cells[1].text = cr.time_basis or "-"
        std_unit = cr.standard_unit or ""
        row.cells[2].text = f"{cr.standard_value:.4g} {std_unit}".strip() if cr.standard_value is not None else "-"
        row.cells[3].text = f"{cr.measured_avg:.4g} {std_unit}".strip() if cr.measured_avg is not None else "-"

        if cr.status == CheckStatus.PASS:
            row.cells[4].text = "적합"
        elif cr.status == CheckStatus.FAIL:
            row.cells[4].text = "초과"
        else:
            row.cells[4].text = "-"

        # 초과 시 빨간색
        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(9)
                    if cr.status == CheckStatus.FAIL:
                        run.font.color.rgb = RGBColor(180, 0, 0)


def _add_evidence_table(doc: Document, entries: list[EvidenceEntry]) -> None:
    """근거 데이터 샘플 테이블을 추가한다."""
    if not entries:
        return

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    headers = ["지표", "측정값", "단위", "관측일"]
    for i, header_text in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header_text
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            run.bold = True
            run.font.size = Pt(9)

    for entry in entries:
        row = table.add_row()
        row.cells[0].text = entry.indicator
        row.cells[1].text = entry.value
        row.cells[2].text = entry.unit or "-"
        row.cells[3].text = entry.observed_at[:10] if entry.observed_at else "-"

        for cell in row.cells:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(9)

    widths = [Cm(4), Cm(5), Cm(3), Cm(3)]
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
            fontName=font_name, fontSize=18, leading=24,
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
            fontName=font_name, fontSize=10, leading=15,
            alignment=1,
        ),
        "center_gray": ParagraphStyle(
            "KoCenterGray", parent=base["Normal"],
            fontName=font_name, fontSize=10, leading=15,
            alignment=1, textColor=colors.Color(0.6, 0.6, 0.6),
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
    }


async def generate_pdf(
    db: AsyncSession,
    project_id: uuid.UUID,
    project_name: str,
    *,
    skip_qa_check: bool = False,
) -> tuple[io.BytesIO, str]:
    """PDF 문서를 생성하여 BytesIO와 파일명을 반환한다."""
    if not skip_qa_check:
        qa_result = await run_qa(db, project_id)
        if not qa_result.export_ready:
            raise ValueError(
                f"critical 이슈 {qa_result.summary.critical_count}건이 "
                f"남아 있어 export가 차단되었습니다."
            )

    scaffold = await generate_draft_scaffold(db, project_id)

    # 섹션별 통계/기준비교 데이터 수집
    section_data = {}
    for section in scaffold.sections:
        stats = await calculate_section_statistics(db, project_id, section.section_key)
        check = await check_section_standards(db, project_id, section.section_key)
        section_data[section.section_key] = (stats, check)

    buffer = _build_pdf(scaffold, project_name, section_data)

    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(
        c if c.isascii() and c.isalnum() or c in "-_" else "_"
        for c in project_name.replace(" ", "_")
    )[:50].strip("_") or "draft"
    filename = f"EIA_{safe_name}_{timestamp}.pdf"

    return buffer, filename


def _build_pdf(
    scaffold: DraftScaffold,
    project_name: str,
    section_data: dict,
) -> io.BytesIO:
    """DraftScaffold로부터 reportlab PDF 문서를 생성한다."""
    font_name = _register_korean_font()
    styles = _get_pdf_styles(font_name)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
        title=f"환경영향평가서 — {project_name}",
        author="EIA Draft Copilot",
    )

    story: list = []

    _pdf_add_cover(story, styles, project_name, scaffold.generated_at)
    _pdf_add_toc(story, styles, scaffold)

    for section in scaffold.sections:
        stats, check = section_data.get(section.section_key, (None, None))
        _pdf_add_section(story, styles, font_name, section, stats, check)

    doc.build(story)
    buffer.seek(0)
    return buffer


def _pdf_add_cover(story, styles, project_name, generated_at):
    """표지 페이지."""
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph("환경영향평가서", styles["title"]))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(project_name, styles["subtitle"]))
    story.append(Spacer(1, 2 * cm))
    date_str = generated_at[:10] if len(generated_at) >= 10 else generated_at
    story.append(Paragraph(f"생성일: {date_str}", styles["center"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("EIA Draft Copilot에 의해 자동 생성됨", styles["center_gray"]))
    story.append(PageBreak())


def _pdf_add_toc(story, styles, scaffold):
    """목차 페이지."""
    story.append(Paragraph("목 차", styles["heading1"]))
    story.append(Spacer(1, 0.5 * cm))
    for section in scaffold.sections:
        entry_count = len(section.evidence_entries)
        status = "근거 있음" if entry_count > 0 else "미수집"
        story.append(Paragraph(
            f"{section.order}. {section.title} — {status} ({entry_count}건)",
            styles["body"],
        ))
    story.append(PageBreak())


def _pdf_add_section(story, styles, font_name, section, stats, check):
    """개별 섹션을 PDF에 추가한다. 4부 구조."""
    story.append(Paragraph(f"{section.order}. {section.title}", styles["heading1"]))
    story.append(Paragraph(section.description, styles["italic_desc"]))

    if not section.evidence_entries:
        story.append(Paragraph(
            section.narrative or "데이터가 수집되지 않았습니다.",
            styles["no_data"],
        ))
        story.append(Spacer(1, 0.5 * cm))
        return

    # 가. 현황 및 영향 분석 (서술문)
    story.append(Paragraph("가. 현황 및 영향 분석", styles["heading2"]))
    for line in section.narrative.split("\n"):
        if line.strip():
            story.append(Paragraph(line, styles["body"]))

    # 나. 측정 현황 요약 (통계 테이블)
    if stats and stats.indicator_stats:
        indicator_with_data = [s for s in stats.indicator_stats if s.count > 0]
        if indicator_with_data:
            story.append(Paragraph("나. 측정 현황 요약", styles["heading2"]))
            _pdf_add_stats_table(story, font_name, indicator_with_data, check)

    # 다. 환경기준 비교
    if check and check.indicators:
        measured = [r for r in check.indicators if r.status != CheckStatus.NA]
        if measured:
            story.append(Paragraph("다. 환경기준 비교", styles["heading2"]))
            _pdf_add_standards_table(story, font_name, measured)

    # 라. 측정 데이터 (대표 샘플 5건)
    story.append(Paragraph("라. 측정 데이터", styles["heading2"]))
    sample_entries = section.evidence_entries[:MAX_DETAIL_SAMPLES]
    _pdf_add_evidence_table(story, font_name, sample_entries)
    if len(section.evidence_entries) > MAX_DETAIL_SAMPLES:
        remaining = len(section.evidence_entries) - MAX_DETAIL_SAMPLES
        story.append(Paragraph(
            f"※ 외 {remaining}건은 별첨 참조",
            styles["note"],
        ))
    story.append(Spacer(1, 0.5 * cm))


def _make_cell_style(font_name: str, size: int = 8, alignment: int = 0) -> ParagraphStyle:
    """PDF 테이블 셀 스타일을 생성한다."""
    return ParagraphStyle(
        f"Cell{size}_{alignment}",
        fontName=font_name, fontSize=size, leading=size + 3,
        alignment=alignment,
    )


def _make_header_style(font_name: str) -> ParagraphStyle:
    """PDF 테이블 헤더 스타일."""
    return ParagraphStyle(
        "TblHeader",
        fontName=font_name, fontSize=9, leading=12,
        alignment=1, textColor=colors.white,
    )


_TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.2, 0.3, 0.5)),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
     [colors.white, colors.Color(0.95, 0.95, 0.97)]),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
])


def _pdf_add_stats_table(story, font_name, indicator_stats, check):
    """통계 요약 테이블을 PDF에 추가한다."""
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

    for s in indicator_stats:
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
            else:
                row.extend([Paragraph("-", cell_s), Paragraph("-", cell_s)])
        data.append(row)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_TABLE_STYLE)
    story.append(table)


def _pdf_add_standards_table(story, font_name, check_results):
    """환경기준 비교 테이블을 PDF에 추가한다."""
    header_s = _make_header_style(font_name)
    cell_s = _make_cell_style(font_name)

    data = [[
        Paragraph("지표", header_s), Paragraph("시간기준", header_s),
        Paragraph("환경기준", header_s), Paragraph("측정평균", header_s),
        Paragraph("판정", header_s),
    ]]

    for cr in check_results:
        std_unit = cr.standard_unit or ""
        std_str = f"{cr.standard_value:.4g} {std_unit}".strip() if cr.standard_value is not None else "-"
        avg_str = f"{cr.measured_avg:.4g} {std_unit}".strip() if cr.measured_avg is not None else "-"

        if cr.status == CheckStatus.PASS:
            status = "적합"
        elif cr.status == CheckStatus.FAIL:
            status = "초과"
        else:
            status = "-"

        data.append([
            Paragraph(cr.indicator, cell_s),
            Paragraph(cr.time_basis or "-", cell_s),
            Paragraph(std_str, cell_s),
            Paragraph(avg_str, cell_s),
            Paragraph(status, cell_s),
        ])

    col_widths = [3.5 * cm, 2.5 * cm, 3.5 * cm, 3.5 * cm, 2 * cm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(_TABLE_STYLE)
    story.append(table)


def _pdf_add_evidence_table(story, font_name, entries):
    """근거 데이터 샘플 테이블을 PDF에 추가한다."""
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
    table.setStyle(_TABLE_STYLE)
    story.append(table)
