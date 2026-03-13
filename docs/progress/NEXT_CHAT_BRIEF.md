# Next Chat Brief

## 마지막 완료 작업
**Reg-2: 서술문 법적 근거 반영** ✅

## 완료된 작업 (Reg-2)

### standard_checker.py — IndicatorCheckResult에 legal_basis 필드 추가
- `IndicatorCheckResult` 데이터클래스에 `legal_basis: str = ""` 필드 추가
- `_check_indicator()`, `check_section_standards()` 에서 `legal_basis` 전달
- `_format_legal_ref()` 헬퍼: 법적 근거 문자열을 서술문 형태로 변환

### narrative_generator.py — 서술문에 법적 근거 자동 삽입
- 매체별 법적 근거 상수 추가 (`_AIR_LEGAL_PREFIX`, `_WATER_LEGAL_PREFIX`, `_NOISE_LEGAL_PREFIX`)
- 대기: "환경정책기본법 시행령 별표 제1호에 따른 대기환경기준(연평균 50 ug/m3)"
- 수질: "환경정책기본법 시행령 별표 제1호에 따른 하천 수질 및 수생태계 생활환경기준 Ib등급(좋음, BOD 2 mg/L 이하)"
- 소음: '환경정책기본법 시행령 별표 제1호에 따른 소음환경기준(일반지역 "나" 야간 45 dB(A))'
- 토양/범용: `IndicatorCheckResult.legal_basis` 기반 조건부 삽입

### draft_scaffold.py — 환경기준 비교 테이블에 "법적 근거" 열 추가
- `_short_legal_ref()` 헬퍼: 간략 표기 ("환경정책기본법 별표1", "토양환경보전법 별표3")
- 테이블 헤더 및 데이터 행에 법적 근거 열 추가

### export_service.py — DOCX/PDF 법적 근거 열 반영
- DOCX: 5→6열, 열 너비 조정
- PDF: 5→6열, 열 너비 조정
- `_short_legal_ref()` 헬퍼 동일 로직 적용

### 프론트엔드
- 변경 불필요: `scaffold-section-view.tsx`에서 `summary_text`를 `<pre>` 태그로 렌더링하므로 자동 반영

### 테스트
- 14개 신규 테스트 추가 (323개 전체 통과)
- `TestLegalBasisInNarrative` (8): 대기/수질/소음/토양 서술문 법적 근거 검증
- `TestLegalBasisInScaffold` (2): 테이블 법적 근거 열 검증
- `TestLegalBasisInStandardChecker` (4): 필드 및 변환 함수 검증

## 전체 Phase 완료 현황
- Phase 0~6: MVP 완료 ✅
- Post-0.5 ~ Post-11: Post-MVP 개선 완료 ✅
- Reg-0: 경미한 이슈 수정 ✅ (Post-11에서 처리)
- Reg-1: 법령 데이터 구축 ✅
- Reg-2: 서술문 법적 근거 반영 ✅

## 다음 작업: Reg-3 (필수 평가 항목 검증 강화)

### 범위
1. section_planner.py 수정 — required_items.py 데이터를 활용한 사업유형별 필수 항목 검증
2. qa_engine.py 수정 — 사업유형 기반 누락 항목 검출 규칙 추가
3. 프로젝트 모델에 사업유형(project_type) 필드 추가 고려
4. 테스트 작성

### 참조
- `docs/regulation-phase-plan.md` — Reg-3 프롬프트 참조
- `backend/app/data/regulations/required_items.py` — 12개 사업유형별 필수 항목 데이터

## 시스템 전체 현황

### 백엔드 서비스 (8개)
| 서비스 | 역할 |
|--------|------|
| section_planner.py | 11개 섹션 정의 + 필수 지표 충족도 계산 |
| draft_scaffold.py | 초안 뼈대 생성 (LLM 서술문 우선 → 템플릿 fallback) |
| statistics.py | 지표별 기술 통계 (평균, 최대, 최소, 표준편차) |
| standard_checker.py | 대기/수질/소음/토양 환경기준 비교 + 등급 판정 + 법적 근거 |
| narrative_generator.py | 섹션별 서술문 템플릿 (대기/수질/소음/생태/범용) + 법적 근거 자동 삽입 |
| similarity.py | 유사사례 가중 유사도 계산 |
| qa_engine.py | 6개 QA 규칙 (R001~R006) |
| export_service.py | DOCX/PDF 생성 (표지+목차+4부 구조+부록 A/B/C) + 법적 근거 열 |

### 법령 데이터 (Reg-1 신규)
| 파일 | 역할 |
|------|------|
| regulations/legal_references.py | 환경기준별 법적 근거 매핑 |
| regulations/required_items.py | 사업유형별 필수 평가 항목 (12개 유형) |
| regulations/area_classifications.py | 소음 지역구분별 기준 차등 |

### 커넥터 (6종)
| 커넥터 키 | 대상 API | 수집 지표 |
|-----------|----------|-----------|
| `keco_air` | 에어코리아 대기오염정보 | PM10, PM2.5, O3, NO2, SO2, CO |
| `water_info` | 국립환경과학원 수질 DB | BOD, COD, SS, DO, T-N, T-P |
| `soil_info` | 국립환경과학원 토양측정망 | Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 |
| `kma_weather` | 기상청 ASOS 일자료 | 평균기온, 최고/최저기온, 강수량, 풍속, 습도 |
| `vworld_land_use` | V-world 2D데이터 | 용도지역구분, 용도지구, 지목 |
| `cultural_heritage` | 국가유산청 Open API | 문화재명, 종별, 이격거리, 소재지 |

### 테스트 (323개)
- test_connectors.py (69), test_regulations.py (53), test_export_format.py (40+)
- test_narrative_generator.py (51), test_llm_adapter.py (29), test_standard_checker.py (27)
- test_spec_alignment.py (23), test_statistics.py (16)
- test_projects.py (9), test_export_pdf.py (4), test_e2e.py (1)

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`backend/.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
- **V-world API 키**: `VWORLD_API_KEY` (.env에 설정)
- **국가유산청 API**: 키 불필요 (공개 API)
- **LLM adapter 사용 시** (선택):
  - `LLM_ADAPTER=openai_paid` + `OPENAI_API_KEY=...`
  - `LLM_ADAPTER=gemini_free` + `GOOGLE_API_KEY=...`
  - 기본값 `LLM_ADAPTER=none` → LLM 없이 동작
- 마이그레이션 실행: `cd backend && alembic upgrade head`
- 프론트엔드 환경변수: `NEXT_PUBLIC_API_URL` (기본값 http://localhost:8000)

## 실행 방법
```bash
# 프론트엔드
npm run dev    # http://localhost:3000

# 백엔드
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload    # http://localhost:8000

# 테스트
cd backend
pytest tests/ -v    # 323개 테스트

# 통합 데모 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py
```
