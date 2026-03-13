# Next Chat Brief

## 마지막 완료 작업
**Post-10: 전체 문서 최신화 + 프론트엔드 지표명 정합성** ✅

## 완료된 작업 (Post-10)

### 전체 문서 Post-9 기준 최신화
- README, architecture, api-reference, development, user-guide 5개 문서 갱신
- 커넥터 4→6종, 테스트 230→247개, Alembic 3→4개, 필수 지표명 정합성 반영

### 프론트엔드 수동 입력 지표명 정합성
- evidence-form-dialog: 토지이용(용도지역구분, 용도지구, 지목), 문화재(문화재명) 수정
- 커넥터 자동 수집 가능 안내 힌트 추가

### 개선 계획 문서 최신화
- post-mvp-improvement-plan.md: Post-1~Post-9 전체 완료 체크 반영

## 전체 Phase 완료 현황
- Phase 0: 스캐폴딩 ✅
- Phase 1: Project CRUD & Backend API ✅
- Phase 2: 데이터 커넥터 & Evidence 인프라 ✅
- Phase 3: Evidence Workbench UI ✅
- Phase 4: 유사사례 매칭 시스템 ✅
- Phase 5: 섹션 플래너 + 초안 뼈대 ✅
- Phase 6: QA 규칙 엔진 + Export Gate + DOCX/PDF 출력 ✅ (MVP 완료)
- Post-0.5: 스펙 정렬 ✅
- Post-1: 데이터 전처리 및 통계 엔진 ✅
- Post-2: 환경기준 비교 엔진 ✅
- Post-3: 초안 텍스트 생성기 고도화 ✅
- Post-4: 추가 커넥터 (토양, 기후) + 수동 입력 가이드 ✅
- Post-5: 문서 포맷 고도화 ✅
- Post-6: LLM adapter 연동 ✅
- Post-7: 통합 테스트 및 최종 데모 ✅
- Post-8: 데이터 파이프라인 정합성 수정 ✅
- Post-9: 커넥터 2종 추가 + DOCX/LLM 수정 ✅
- Post-10: 전체 문서 최신화 + 프론트엔드 지표명 정합성 ✅

## 시스템 전체 현황

### 백엔드 서비스 (8개)
| 서비스 | 역할 |
|--------|------|
| section_planner.py | 11개 섹션 정의 + 필수 지표 충족도 계산 |
| draft_scaffold.py | 초안 뼈대 생성 (LLM 서술문 우선 → 템플릿 fallback) |
| statistics.py | 지표별 기술 통계 (평균, 최대, 최소, 표준편차) |
| standard_checker.py | 대기/수질/소음/토양 환경기준 비교 + 등급 판정 |
| narrative_generator.py | 섹션별 서술문 템플릿 (대기/수질/소음/생태/범용) |
| similarity.py | 유사사례 가중 유사도 계산 |
| qa_engine.py | 6개 QA 규칙 (R001~R006) |
| export_service.py | DOCX/PDF 생성 (표지+목차+4부 구조+부록 A/B/C) |

### 커넥터 (6종)
| 커넥터 키 | 대상 API | 수집 지표 |
|-----------|----------|-----------|
| `keco_air` | 에어코리아 대기오염정보 | PM10, PM2.5, O3, NO2, SO2, CO |
| `water_info` | 국립환경과학원 수질 DB | BOD, COD, SS, DO, T-N, T-P |
| `soil_info` | 국립환경과학원 토양측정망 | Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 |
| `kma_weather` | 기상청 ASOS 일자료 | 평균기온, 최고/최저기온, 강수량, 풍속, 습도 |
| `vworld_land_use` | V-world 2D데이터 | 용도지역구분, 용도지구, 지목 |
| `cultural_heritage` | 국가유산청 Open API | 문화재명, 종별, 이격거리, 소재지 |

### LLM Adapter (3종)
| Adapter | 모델 | 설명 |
|---------|------|------|
| none | - | LLM 미사용 (기본값, MVP 동작) |
| openai_paid | gpt-4o-mini | OpenAI GPT |
| gemini_free | gemini-2.0-flash | Google Gemini (무료 티어) |

### 테스트 (247개)
- test_connectors.py (69), test_export_format.py (40+), test_llm_adapter.py (29)
- test_narrative_generator.py (28), test_standard_checker.py (27)
- test_spec_alignment.py (23), test_statistics.py (16)
- test_projects.py (9), test_export_pdf.py (4), test_e2e.py (1)

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`backend/.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
  - 4개 커넥터 사용 (keco_air, water_info, soil_info, kma_weather)
- **V-world API 키**: `VWORLD_API_KEY` (.env에 설정)
  - 토지이용 커넥터 사용
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
pytest tests/ -v    # 247개 테스트

# 통합 데모 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py
```
