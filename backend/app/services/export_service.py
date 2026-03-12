"""DOCX/PDF 출력 서비스.

초안 뼈대(DraftScaffold) 데이터를 기반으로 DOCX 문서를 생성한다.
python-docx를 사용하며, 섹션 구조 · 근거 테이블 · 요약문을 포함한다.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.draft_scaffold import (
    DraftScaffold,
    ScaffoldSection,
    generate_draft_scaffold,
)
from app.services.qa_engine import run_qa


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

    # DOCX 문서 생성
    doc = _build_docx(scaffold, project_name)

    # BytesIO로 직렬화
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # 파일명 생성 (HTTP 헤더 latin-1 호환을 위해 ASCII 안전 처리)
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    # 한글 등 비ASCII 문자를 제거하고 ASCII 안전 파일명 생성
    safe_name = "".join(
        c if c.isascii() and c.isalnum() or c in "-_" else "_"
        for c in project_name.replace(" ", "_")
    )[:50].strip("_") or "draft"
    filename = f"EIA_{safe_name}_{timestamp}.docx"

    return buffer, filename


def _build_docx(scaffold: DraftScaffold, project_name: str) -> Document:
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
        _add_section(doc, section)

    return doc


def _add_cover_page(doc: Document, project_name: str, generated_at: str) -> None:
    """표지 페이지를 추가한다."""
    # 빈 줄 추가 (상단 여백)
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


def _add_section(doc: Document, section: ScaffoldSection) -> None:
    """개별 섹션을 DOCX에 추가한다."""
    doc.add_heading(f"{section.order}. {section.title}", level=1)
    doc.add_paragraph(section.description).italic = True

    if not section.evidence_entries:
        para = doc.add_paragraph(
            f"{section.title} 분야에 대한 수집된 증거 데이터가 없습니다."
        )
        para.runs[0].font.color.rgb = RGBColor(180, 0, 0)
        doc.add_paragraph("")
        return

    # 요약문 추가
    doc.add_heading("현황 요약", level=2)
    for line in section.summary_text.split("\n"):
        if line.strip():
            doc.add_paragraph(line)

    # 근거 데이터 테이블
    doc.add_heading("근거 데이터 목록", level=2)
    _add_evidence_table(doc, section)

    doc.add_paragraph("")


def _add_evidence_table(doc: Document, section: ScaffoldSection) -> None:
    """근거 데이터를 테이블로 추가한다."""
    entries = section.evidence_entries
    if not entries:
        return

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    # 헤더
    headers = ["지표", "측정값", "단위", "관측일"]
    for i, header_text in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header_text
        para = cell.paragraphs[0]
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in para.runs:
            run.bold = True
            run.font.size = Pt(9)

    # 데이터 행
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

    # 컬럼 너비 설정
    widths = [Cm(4), Cm(5), Cm(3), Cm(3)]
    for row in table.rows:
        for i, width in enumerate(widths):
            row.cells[i].width = width
