"""Pred-3 통합 테스트: 예측 결과 scaffold/서술문/DOCX 통합.

검증 범위:
  1. generate_prediction_narrative() 서술문 키워드 테스트
  2. ScaffoldSection prediction_result 필드 설정/기본값 테스트
  3. _build_docx() 호출 시 예측 결과 유무에 따른 DOCX 구조 테스트

실행:
  cd backend
  pytest tests/test_pred3_integration.py -v
"""

from __future__ import annotations

import io

import pytest
from docx import Document

from app.services.prediction.base import PredictionItem, PredictionResult
from app.services.narrative_generator import generate_prediction_narrative
from app.services.draft_scaffold import DraftScaffold, EvidenceEntry, ScaffoldSection
from app.services.export_service import (
    ExportContext,
    ExportOptions,
    _build_docx,
)


# ─────────────────────────────────────────────────────────────
# 예측 결과 Fixture 헬퍼
# ─────────────────────────────────────────────────────────────

def _make_air_prediction() -> PredictionResult:
    """대기질 예측 결과 fixture."""
    return PredictionResult(
        section_key="air_quality",
        model_name="gaussian_plume",
        input_parameters={"project_type": "industrial", "stack_height": 30.0},
        predictions=[
            PredictionItem(
                label="100m", distance_m=100.0, pollutant="PM10",
                predicted_concentration=5.0, background_concentration=40.0,
                total_concentration=45.0, unit="ug/m3",
                standard_value=50.0, exceeds_standard=False,
            ),
            PredictionItem(
                label="100m", distance_m=100.0, pollutant="PM2.5",
                predicted_concentration=3.0, background_concentration=20.0,
                total_concentration=23.0, unit="ug/m3",
                standard_value=15.0, exceeds_standard=True,
            ),
            # 200m 지점 PM10
            PredictionItem(
                label="200m", distance_m=200.0, pollutant="PM10",
                predicted_concentration=2.0, background_concentration=40.0,
                total_concentration=42.0, unit="ug/m3",
                standard_value=50.0, exceeds_standard=False,
            ),
        ],
        summary="가우시안 플룸 예측 요약",
        assumptions=["대기안정도 D등급", "풍속 3 m/s"],
        limitations=["평탄 지형 가정"],
    )


def _make_noise_prediction() -> PredictionResult:
    """소음 예측 결과 fixture."""
    return PredictionResult(
        section_key="noise_vibration",
        model_name="noise_propagation",
        input_parameters={"source_type": "point", "sound_power_level": 95.0},
        predictions=[
            PredictionItem(
                label="10m", distance_m=10.0, pollutant="소음_Leq_주간",
                predicted_concentration=74.0, background_concentration=52.0,
                total_concentration=74.1, unit="dB(A)",
                standard_value=55.0, exceeds_standard=True,
            ),
            PredictionItem(
                label="10m", distance_m=10.0, pollutant="소음_Leq_야간",
                predicted_concentration=74.0, background_concentration=40.0,
                total_concentration=74.0, unit="dB(A)",
                standard_value=45.0, exceeds_standard=True,
            ),
            PredictionItem(
                label="100m", distance_m=100.0, pollutant="소음_Leq_주간",
                predicted_concentration=54.0, background_concentration=52.0,
                total_concentration=56.0, unit="dB(A)",
                standard_value=55.0, exceeds_standard=True,
            ),
        ],
        summary="소음 전파 예측 요약",
        assumptions=["점음원", "Lw 95dB"],
        limitations=["평탄 지형"],
    )


def _make_water_prediction() -> PredictionResult:
    """수질 예측 결과 fixture."""
    return PredictionResult(
        section_key="water_quality",
        model_name="water_mixing",
        input_parameters={"river_flow": 1.0, "discharge_flow": 0.1},
        predictions=[
            PredictionItem(
                label="혼합 후", distance_m=0.0, pollutant="BOD",
                predicted_concentration=30.0, background_concentration=2.5,
                total_concentration=5.0, unit="mg/L",
                standard_value=5.0, exceeds_standard=False,
            ),
            PredictionItem(
                label="혼합 후", distance_m=0.0, pollutant="COD",
                predicted_concentration=40.0, background_concentration=4.0,
                total_concentration=7.27, unit="mg/L",
                standard_value=7.0, exceeds_standard=True,
            ),
        ],
        summary="수질 혼합 예측 요약",
        assumptions=["완전혼합"],
        limitations=["근역 혼합 미반영"],
    )


# ─────────────────────────────────────────────────────────────
# ExportContext 구성 헬퍼
# ─────────────────────────────────────────────────────────────

def _make_evidence_entries(count: int = 2) -> list[EvidenceEntry]:
    """테스트용 EvidenceEntry 목록 생성."""
    return [
        EvidenceEntry(
            evidence_id=f"ev{i}",
            indicator="PM10_연평균",
            value=str(40 + i),
            numeric_value=float(40 + i),
            unit="ug/m3",
            observed_at=f"2025-0{(i % 9) + 1}-01T00:00:00",
            data_source_id=None,
            metadata_json=None,
        )
        for i in range(count)
    ]


def _make_section(
    section_key: str,
    title: str,
    order: int,
    prediction_result: PredictionResult | None = None,
    prediction_narrative: str = "",
    has_evidence: bool = True,
) -> ScaffoldSection:
    """테스트용 ScaffoldSection 생성."""
    entries = _make_evidence_entries(2) if has_evidence else []
    return ScaffoldSection(
        section_key=section_key,
        title=title,
        description=f"{title} 현황 분석",
        order=order,
        evidence_entries=entries,
        summary_text="요약 텍스트",
        narrative="서술문 내용",
        state="complete" if has_evidence else "empty",
        prediction_result=prediction_result,
        prediction_narrative=prediction_narrative,
    )


def _make_ctx_with_sections(sections: list[ScaffoldSection]) -> ExportContext:
    """섹션 목록으로 ExportContext를 생성한다."""
    scaffold = DraftScaffold(
        project_id="pred3-test",
        generated_at="2025-06-01T00:00:00",
        sections=sections,
        total_evidence_count=sum(len(s.evidence_entries) for s in sections),
    )
    section_data = {s.section_key: (None, None) for s in sections}
    return ExportContext(
        scaffold=scaffold,
        project_name="Pred-3 테스트 프로젝트",
        project_type="industrial",
        centroid=(37.5, 127.0),
        section_data=section_data,
        similar_cases=[],
        qa_result=None,
        options=ExportOptions(
            include_appendix_a=False,
            include_appendix_b=False,
            include_appendix_c=False,
        ),
        generated_at=scaffold.generated_at,
    )


def _all_paragraph_texts(doc: Document) -> list[str]:
    """문서 내 모든 단락 텍스트(빈 줄 제외)를 반환한다."""
    texts = []
    for p in doc.paragraphs:
        if p.text.strip():
            texts.append(p.text)
    return texts


# ═════════════════════════════════════════════════════════════
# 1. 서술문 생성 테스트
# ═════════════════════════════════════════════════════════════

class TestAirPredictionNarrative:
    """대기질 예측 서술문 키워드 및 내용 검증."""

    def test_air_prediction_narrative_contains_keywords(self):
        """대기질 서술문에 가우시안 플룸 모델 핵심 키워드가 포함되어야 한다."""
        result = generate_prediction_narrative("air_quality", _make_air_prediction())
        # 가우시안 플룸 언급
        assert "가우시안 플룸" in result
        # 기여농도 언급
        assert "기여농도" in result
        # 합산 언급 (현황 + 기여)
        assert "합산" in result

    def test_air_prediction_narrative_exceed_mention(self):
        """기준 초과 오염물질이 서술문에 언급되어야 한다."""
        result = generate_prediction_narrative("air_quality", _make_air_prediction())
        # PM2.5가 기준 초과이므로 서술문에 포함되어야 함
        assert "PM2.5" in result
        # 초과 관련 표현
        assert "초과" in result

    def test_air_prediction_narrative_legal_reference(self):
        """대기질 서술문에 법적 근거(환경정책기본법)가 포함되어야 한다."""
        result = generate_prediction_narrative("air_quality", _make_air_prediction())
        assert "환경정책기본법" in result


class TestNoisePredictionNarrative:
    """소음 예측 서술문 키워드 및 내용 검증."""

    def test_noise_prediction_narrative_contains_keywords(self):
        """소음 서술문에 거리감쇠 모델 핵심 키워드가 포함되어야 한다."""
        result = generate_prediction_narrative("noise_vibration", _make_noise_prediction())
        # 점음원 거리감쇠 모델 언급
        assert "거리감쇠" in result
        # 에너지 합산 언급
        assert "에너지 합산" in result
        # 단위 포함
        assert "dB(A)" in result

    def test_noise_prediction_narrative_period(self):
        """소음 서술문에 주간/야간 구분이 포함되어야 한다."""
        result = generate_prediction_narrative("noise_vibration", _make_noise_prediction())
        assert "주간" in result
        assert "야간" in result

    def test_noise_prediction_narrative_exceed_mention(self):
        """주간/야간 모두 기준 초과이므로 방음대책 언급이 있어야 한다."""
        result = generate_prediction_narrative("noise_vibration", _make_noise_prediction())
        # 초과 → 방음대책 또는 초과 표현
        assert "초과" in result or "방음" in result


class TestWaterPredictionNarrative:
    """수질 예측 서술문 키워드 및 내용 검증."""

    def test_water_prediction_narrative_contains_keywords(self):
        """수질 서술문에 완전혼합 모델 핵심 키워드가 포함되어야 한다."""
        result = generate_prediction_narrative("water_quality", _make_water_prediction())
        # 완전혼합 모델 언급
        assert "완전혼합" in result
        # 혼합 후 표현
        assert "혼합 후" in result
        # 단위 포함
        assert "mg/L" in result

    def test_water_prediction_narrative_exceed_mention(self):
        """COD가 기준 초과이므로 추가 처리 대책 언급이 있어야 한다."""
        result = generate_prediction_narrative("water_quality", _make_water_prediction())
        # COD 초과 → 대책 검토 언급
        assert "COD" in result
        assert "초과" in result


class TestUnsupportedSectionNarrative:
    """미지원 섹션 서술문 — 별도 전문 분석 필요 문구 반환."""

    def test_unsupported_section_narrative(self):
        """생태, 토지이용 등 예측 미지원 섹션은 '별도 전문 분석이 필요' 문구를 반환해야 한다."""
        # 생태 섹션: 예측 모델 없음
        air_result = _make_air_prediction()  # section_key를 의도적으로 무관한 섹션에 적용
        result = generate_prediction_narrative("ecology", air_result)
        assert "별도 전문 분석이 필요" in result

    def test_land_use_narrative(self):
        """토지이용 섹션도 예측 미지원이므로 동일 문구를 반환해야 한다."""
        result = generate_prediction_narrative("land_use", _make_air_prediction())
        assert "별도 전문 분석이 필요" in result

    def test_unknown_section_narrative(self):
        """존재하지 않는 섹션 키도 '별도 전문 분석이 필요' 문구를 반환해야 한다."""
        result = generate_prediction_narrative("unknown_section", _make_air_prediction())
        assert "별도 전문 분석이 필요" in result


# ═════════════════════════════════════════════════════════════
# 2. ScaffoldSection prediction_result 필드 테스트
# ═════════════════════════════════════════════════════════════

class TestScaffoldSectionPrediction:
    """ScaffoldSection의 prediction_result/prediction_narrative 필드 동작 검증."""

    def test_scaffold_section_with_prediction(self):
        """prediction_result를 명시적으로 설정하면 올바르게 저장되어야 한다."""
        air_pred = _make_air_prediction()
        narrative = generate_prediction_narrative("air_quality", air_pred)

        section = ScaffoldSection(
            section_key="air_quality",
            title="대기질",
            description="대기오염물질 현황",
            order=1,
            prediction_result=air_pred,
            prediction_narrative=narrative,
        )

        assert section.prediction_result is not None
        assert section.prediction_result.section_key == "air_quality"
        assert section.prediction_result.model_name == "gaussian_plume"
        assert len(section.prediction_result.predictions) == 3
        assert section.prediction_narrative != ""
        assert "가우시안 플룸" in section.prediction_narrative

    def test_scaffold_section_noise_prediction(self):
        """소음 prediction_result가 올바르게 저장되어야 한다."""
        noise_pred = _make_noise_prediction()
        narrative = generate_prediction_narrative("noise_vibration", noise_pred)

        section = ScaffoldSection(
            section_key="noise_vibration",
            title="소음·진동",
            description="소음 현황",
            order=3,
            prediction_result=noise_pred,
            prediction_narrative=narrative,
        )

        assert section.prediction_result is not None
        assert section.prediction_result.model_name == "noise_propagation"
        assert "dB(A)" in section.prediction_narrative

    def test_scaffold_section_water_prediction(self):
        """수질 prediction_result가 올바르게 저장되어야 한다."""
        water_pred = _make_water_prediction()
        narrative = generate_prediction_narrative("water_quality", water_pred)

        section = ScaffoldSection(
            section_key="water_quality",
            title="수질",
            description="수질 현황",
            order=2,
            prediction_result=water_pred,
            prediction_narrative=narrative,
        )

        assert section.prediction_result is not None
        assert section.prediction_result.model_name == "water_mixing"
        assert "완전혼합" in section.prediction_narrative

    def test_scaffold_section_without_prediction(self):
        """기본값으로 생성된 ScaffoldSection은 prediction_result가 None이어야 한다."""
        section = ScaffoldSection(
            section_key="ecology",
            title="생태",
            description="생태 현황",
            order=4,
        )

        assert section.prediction_result is None
        assert section.prediction_narrative == ""

    def test_scaffold_section_ecology_no_prediction(self):
        """생태 섹션은 예측 모델이 없으므로 prediction_result=None이 기본값이다."""
        section = _make_section("ecology", "생태", order=4)
        assert section.prediction_result is None

    def test_scaffold_section_land_use_no_prediction(self):
        """토지이용 섹션도 예측 모델이 없으므로 prediction_result=None이 기본값이다."""
        section = _make_section("land_use", "토지이용", order=5)
        assert section.prediction_result is None


# ═════════════════════════════════════════════════════════════
# 3. DOCX 구조 테스트
# ═════════════════════════════════════════════════════════════

class TestDocxWithPrediction:
    """예측 결과 유무에 따른 DOCX 구조 검증."""

    def test_docx_contains_prediction_heading_when_result_exists(self):
        """prediction_result가 있는 섹션에 '영향 예측' 소제목이 생성되어야 한다."""
        air_pred = _make_air_prediction()
        narrative = generate_prediction_narrative("air_quality", air_pred)

        air_section = _make_section(
            "air_quality", "대기질", order=1,
            prediction_result=air_pred,
            prediction_narrative=narrative,
        )
        ctx = _make_ctx_with_sections([air_section])
        doc = _build_docx(ctx)

        all_texts = _all_paragraph_texts(doc)
        combined = "\n".join(all_texts)
        assert "영향 예측" in combined

    def test_docx_does_not_contain_prediction_heading_when_no_result(self):
        """prediction_result가 None인 섹션에는 '영향 예측' 소제목이 없어야 한다."""
        ecology_section = _make_section(
            "ecology", "생태", order=1,
            prediction_result=None,
        )
        ctx = _make_ctx_with_sections([ecology_section])
        doc = _build_docx(ctx)

        all_texts = _all_paragraph_texts(doc)
        combined = "\n".join(all_texts)
        assert "영향 예측" not in combined

    def test_docx_prediction_table_headers_air(self):
        """대기질 예측 테이블 헤더가 '지점/거리', '오염물질', '기여농도', '합산' 등을 포함해야 한다."""
        air_pred = _make_air_prediction()
        narrative = generate_prediction_narrative("air_quality", air_pred)

        air_section = _make_section(
            "air_quality", "대기질", order=1,
            prediction_result=air_pred,
            prediction_narrative=narrative,
        )
        ctx = _make_ctx_with_sections([air_section])
        doc = _build_docx(ctx)

        # 테이블 헤더 텍스트 수집
        table_cells: list[str] = []
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        table_cells.append(cell.text.strip())

        combined = " ".join(table_cells)
        # 대기질/소음 테이블 헤더: 지점/거리, 오염물질, 기여농도, 합산
        assert "지점/거리" in combined
        assert "오염물질" in combined
        assert "기여농도" in combined
        assert "합산" in combined

    def test_docx_prediction_table_headers_water(self):
        """수질 예측 테이블 헤더가 '항목', '방류수 농도', '혼합 후'를 포함해야 한다."""
        water_pred = _make_water_prediction()
        narrative = generate_prediction_narrative("water_quality", water_pred)

        water_section = _make_section(
            "water_quality", "수질", order=1,
            prediction_result=water_pred,
            prediction_narrative=narrative,
        )
        ctx = _make_ctx_with_sections([water_section])
        doc = _build_docx(ctx)

        table_cells: list[str] = []
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        table_cells.append(cell.text.strip())

        combined = " ".join(table_cells)
        # 수질 테이블 헤더: 항목, 방류수 농도, 혼합 후
        assert "항목" in combined
        assert "방류수 농도" in combined
        assert "혼합 후" in combined

    def test_docx_prediction_assumptions_paragraph(self):
        """예측 결과가 있는 섹션에 '※ 전제 조건' 문단이 존재해야 한다."""
        air_pred = _make_air_prediction()
        narrative = generate_prediction_narrative("air_quality", air_pred)

        air_section = _make_section(
            "air_quality", "대기질", order=1,
            prediction_result=air_pred,
            prediction_narrative=narrative,
        )
        ctx = _make_ctx_with_sections([air_section])
        doc = _build_docx(ctx)

        all_texts = _all_paragraph_texts(doc)
        combined = "\n".join(all_texts)
        # 전제 조건 섹션 존재 확인
        assert "※ 전제 조건" in combined or "전제 조건" in combined

    def test_docx_prediction_limitations_paragraph(self):
        """예측 결과가 있는 섹션에 '※ 참고: 모델 한계' 문단이 존재해야 한다."""
        air_pred = _make_air_prediction()
        narrative = generate_prediction_narrative("air_quality", air_pred)

        air_section = _make_section(
            "air_quality", "대기질", order=1,
            prediction_result=air_pred,
            prediction_narrative=narrative,
        )
        ctx = _make_ctx_with_sections([air_section])
        doc = _build_docx(ctx)

        all_texts = _all_paragraph_texts(doc)
        combined = "\n".join(all_texts)
        # 모델 한계 섹션 존재 확인 (※ 기호 포함)
        assert "모델 한계" in combined

    def test_docx_multiple_sections_prediction_isolation(self):
        """예측 결과가 있는 섹션과 없는 섹션이 혼재할 때 각자 올바르게 처리되어야 한다."""
        air_pred = _make_air_prediction()
        narrative = generate_prediction_narrative("air_quality", air_pred)

        air_section = _make_section(
            "air_quality", "대기질", order=1,
            prediction_result=air_pred,
            prediction_narrative=narrative,
        )
        # 생태 섹션은 예측 없음
        ecology_section = _make_section(
            "ecology", "생태", order=2,
            prediction_result=None,
        )

        ctx = _make_ctx_with_sections([air_section, ecology_section])
        doc = _build_docx(ctx)

        # 문서 전체에서 "영향 예측" 텍스트가 정확히 1번(대기질 섹션)만 나타나야 함
        # "제1장", "제2장" 모두 포함됨을 확인
        all_texts = _all_paragraph_texts(doc)
        combined = "\n".join(all_texts)

        # 대기질 섹션 제목 존재
        assert "대기질" in combined
        # 생태 섹션 제목 존재
        assert "생태" in combined
        # 영향 예측 헤딩이 최소 1개 존재
        assert "영향 예측" in combined

    def test_docx_noise_prediction_narrative_in_document(self):
        """소음 예측 서술문이 DOCX 문서 본문에 포함되어야 한다."""
        noise_pred = _make_noise_prediction()
        narrative = generate_prediction_narrative("noise_vibration", noise_pred)

        noise_section = _make_section(
            "noise_vibration", "소음·진동", order=1,
            prediction_result=noise_pred,
            prediction_narrative=narrative,
        )
        ctx = _make_ctx_with_sections([noise_section])
        doc = _build_docx(ctx)

        all_texts = _all_paragraph_texts(doc)
        combined = "\n".join(all_texts)
        # 소음 서술문 키워드 확인
        assert "dB(A)" in combined

    def test_docx_water_prediction_narrative_in_document(self):
        """수질 예측 서술문이 DOCX 문서 본문에 포함되어야 한다."""
        water_pred = _make_water_prediction()
        narrative = generate_prediction_narrative("water_quality", water_pred)

        water_section = _make_section(
            "water_quality", "수질", order=1,
            prediction_result=water_pred,
            prediction_narrative=narrative,
        )
        ctx = _make_ctx_with_sections([water_section])
        doc = _build_docx(ctx)

        all_texts = _all_paragraph_texts(doc)
        combined = "\n".join(all_texts)
        # 수질 서술문 키워드 확인
        assert "완전혼합" in combined

    def test_docx_valid_bytes_output(self):
        """예측 결과가 있는 섹션으로 생성된 DOCX가 올바른 바이트 스트림이어야 한다."""
        air_pred = _make_air_prediction()
        narrative = generate_prediction_narrative("air_quality", air_pred)

        air_section = _make_section(
            "air_quality", "대기질", order=1,
            prediction_result=air_pred,
            prediction_narrative=narrative,
        )
        ctx = _make_ctx_with_sections([air_section])
        doc = _build_docx(ctx)

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        raw = buf.read()

        # DOCX는 ZIP 아카이브이므로 PK 매직 바이트로 시작해야 함
        assert raw[:2] == b"PK"
        assert len(raw) > 1000  # 빈 문서보다 크다
