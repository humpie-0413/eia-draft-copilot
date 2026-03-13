# Next Chat Brief

## 마지막 완료 작업
**Post-8: 데이터 파이프라인 정합성 수정** ✅

## 완료된 작업 (Post-8)

### 지표명 정합성 수정
- 토양 섹션: required_indicators를 커넥터 출력(Pb, Cd, pH, 유기물함량)과 일치
- 기후 섹션: required_indicators를 커넥터 출력(평균기온, 강수량, 평균풍속)과 일치
- 토양 환경기준 추가: 토양환경보전법 시행규칙 별표 3 기준 6개 지표

### 데모 스크립트 fallback 로직 수정
- 커넥터 status=error 시 수동 fallback 정상 작동 (기존: HTTP 실패 시에만)
- 수질 필수 지표 수동 보충 단계(2-b2) 추가
  - API가 과거 데이터(1992~2000) 반환 시 통계 엔진 5년 필터 통과 보장
- 토양/기후 fallback 지표명을 커넥터 출력과 일치

### 검증 결과
- 230개 전체 테스트 통과
- 데모 11단계 정상 실행: 수질/토양/기후 모두 서술문+통계 생성 확인
- DOCX/PDF 출력: 표지+목차+11섹션+부록 A/B/C 정상

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

## 시스템 전체 현황

### 백엔드 서비스 (8개)
| 서비스 | 역할 |
|--------|------|
| section_planner.py | 11개 섹션 정의 + 필수 지표 충족도 계산 |
| draft_scaffold.py | 초안 뼈대 생성 (통계 요약 + 기준비교 + 샘플) |
| statistics.py | 지표별 기술 통계 (평균, 최대, 최소, 표준편차) |
| standard_checker.py | 대기/수질/소음/토양 환경기준 비교 + 등급 판정 |
| narrative_generator.py | 섹션별 서술문 템플릿 (대기/수질/소음/생태/범용) |
| similarity.py | 유사사례 가중 유사도 계산 |
| qa_engine.py | 6개 QA 규칙 (R001~R006) |
| export_service.py | DOCX/PDF 생성 (표지+목차+4부 구조+부록 A/B/C) |

### 커넥터 (4종)
| 커넥터 키 | 대상 API | 수집 지표 |
|-----------|----------|-----------|
| `keco_air` | 에어코리아 대기오염정보 | PM10, PM2.5, O3, NO2, SO2, CO |
| `water_info` | 국립환경과학원 수질 DB | BOD, COD, SS, DO, T-N, T-P |
| `soil_info` | 국립환경과학원 토양측정망 | Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 |
| `kma_weather` | 기상청 ASOS 일자료 | 평균기온, 최고/최저기온, 강수량, 풍속, 습도 |

### LLM Adapter (3종)
| Adapter | 모델 | 설명 |
|---------|------|------|
| none | - | LLM 미사용 (기본값, MVP 동작) |
| openai_paid | gpt-4o-mini | OpenAI GPT |
| gemini_free | gemini-2.0-flash | Google Gemini (무료 티어) |

### API 엔드포인트 (11개 라우터)
- projects, evidences, snapshots, data-sources, connectors
- similar-cases, sections, statistics, standards-check
- qa, export, llm

### 테스트 (230개)
- test_connectors.py (52), test_export_format.py (40), test_llm_adapter.py (29)
- test_narrative_generator.py (28), test_standard_checker.py (27)
- test_spec_alignment.py (23), test_statistics.py (16)
- test_projects.py (9), test_export_pdf.py (4), test_e2e.py (1)

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`backend/.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
  - 4개 커넥터 모두 동일 키 사용
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
pytest tests/ -v    # 230개 테스트

# 통합 데모 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py
```
