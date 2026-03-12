# Next Chat Brief

## 마지막 완료 작업
**Post-6: LLM adapter 연동** ✅

## 완료된 작업 (Post-6)

### LLM adapter 인터페이스
- BaseLLMAdapter 추상 클래스 (enhance_narrative 메서드)
- EnhanceInput: 섹션 키, 제목, 템플릿 서술문, 통계 요약, 기준비교 요약
- EnhanceResult: 보강 텍스트, adapter 이름, fallback 여부

### 3종 adapter
- NoneAdapter: 기본값, 템플릿 그대로 반환 (LLM 없이 완전 동작)
- OpenAIAdapter: gpt-4o-mini, OPENAI_API_KEY, fallback 포함
- GeminiAdapter: gemini-2.0-flash, GOOGLE_API_KEY, httpx REST, fallback 포함

### 시스템 프롬프트
- "한국 환경영향평가서 전문 작성자" 역할
- 규칙: 데이터 외 추가 금지, 수치 변경 금지, 공식적 문체, 추측 금지

### adapter 설정
- LLM_ADAPTER 환경변수 (none|openai_paid|gemini_free, 기본: none)
- factory 함수 get_llm_adapter()

### API
- GET /api/v1/llm/status — adapter 상태 및 API 키 조회
- POST /api/v1/llm/projects/{id}/enhance — 섹션 서술문 AI 보강

### 프론트엔드
- ScaffoldSectionView: "AI 문체 보강" 버튼 + 보강 전/후 비교
- LLMStatusCard: 사이드바에 현재 모드 및 키 상태 표시

### 테스트
- 29개 신규 테스트 (test_llm_adapter.py)
- 전체 230개 테스트 통과

## 이전 완료 Phase
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

## 향후 작업 (Post-7)
- Post-7: 통합 테스트 및 최종 데모

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`backend/.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
  - 에어코리아 대기오염정보, 국립환경과학원 수질 DB, 토양측정망, 기상청 ASOS 공유
- **LLM adapter 사용 시** (선택):
  - `LLM_ADAPTER=openai_paid` + `OPENAI_API_KEY=...`
  - `LLM_ADAPTER=gemini_free` + `GOOGLE_API_KEY=...`
  - 기본값 `LLM_ADAPTER=none` → LLM 없이 동작
- python-docx 설치 필요: `pip install python-docx>=1.1.0`
- reportlab 설치 필요: `pip install reportlab>=4.0.0`
- openai 설치 필요: `pip install openai>=1.0.0`
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
pytest tests/ -v

# 데모 실행 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py
```

## 커넥터 현황 (4개)
| 커넥터 키 | 대상 API | 수집 지표 |
|-----------|----------|-----------|
| `keco_air` | 에어코리아 대기오염정보 | PM10, PM2.5, O3, NO2, SO2, CO |
| `water_info` | 국립환경과학원 수질 DB | BOD, COD, SS, DO, T-N, T-P |
| `soil_info` | 국립환경과학원 토양측정망 | Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 |
| `kma_weather` | 기상청 ASOS 일자료 | 평균기온, 최고/최저기온, 강수량, 풍속, 습도 |

## 주요 파일 (Post-6 신규/수정)
- `backend/app/llm/__init__.py` — adapter factory (신규)
- `backend/app/llm/base.py` — BaseLLMAdapter 추상 클래스 (신규)
- `backend/app/llm/none_adapter.py` — None adapter (신규)
- `backend/app/llm/openai_adapter.py` — OpenAI adapter (신규)
- `backend/app/llm/gemini_adapter.py` — Gemini adapter (신규)
- `backend/app/config.py` — LLM_ADAPTER 설정 (수정)
- `backend/app/api/v1/llm.py` — LLM API 엔드포인트 (신규)
- `backend/tests/test_llm_adapter.py` — 29개 테스트 (신규)
- `src/types/llm.ts` — LLM 타입 (신규)
- `src/lib/llm-api.ts` — LLM API 클라이언트 (신규)
- `src/components/section/scaffold-section-view.tsx` — AI 보강 UI (수정)
- `src/components/section/llm-status-card.tsx` — LLM 상태 카드 (신규)
