# Next Chat Brief

## 마지막 완료 작업
**Post-2: 환경기준 비교 엔진** ✅

## 완료된 작업 (Post-2)

### 환경기준 데이터
- `backend/app/data/env_standards.py`:
  - 대기환경기준: PM10, PM2.5, SO2, NO2, CO, O3 (연평균/24시간/1시간)
  - 수질환경기준: 하천 생활환경기준 Ia~V등급 (BOD, COD, SS, DO, T-P)
  - 소음환경기준: 주거지역 주간 55dB(A), 야간 45dB(A)
  - 수질 등급 판정 함수 (최악 등급 적용)

### 기준 비교 서비스
- `backend/app/services/standard_checker.py`:
  - 통계 결과 ↔ 환경기준 비교 (pass/fail/na 판정)
  - 수질 등급 판정 포함 (BOD/COD/DO/T-P 기반)
  - 섹션별 기준 비교 요약 서술문 자동 생성

### 기준 비교 API
- `GET /api/v1/projects/{id}/standards-check` — 전체 섹션 기준 비교
- `GET /api/v1/projects/{id}/standards-check/{section_key}` — 개별 섹션
- 쿼리 파라미터: years_filter, aggregate_daily

### scaffold 수정
- 통계 요약 테이블에 "환경기준" + "판정" 열 추가
- 기준 비교 서술문 섹션 추가 (적합/초과 서술 자동 생성)

### QA 규칙
- R006: 환경기준 초과 지표 존재 시 warning (초과 지표명 + 수치 포함)
- warning이므로 export는 차단하지 않음

### 테스트
- `backend/tests/test_standard_checker.py`: 27개 테스트 전부 통과
- 기존 테스트 호환: test_statistics.py 16개, test_e2e.py 1개 모두 통과
- 전체 44개 테스트 통과

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

## 향후 작업 (Post-3+)
- Post-3: 초안 텍스트 생성기 고도화 (통계+기준비교 기반 서술문 자동 생성)
- Post-4: 추가 커넥터 (토양, 기후)
- Post-5: 문서 포맷 고도화
- Post-6: LLM adapter 연동
- Post-7: 통합 테스트 및 최종 데모

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`.env.example` 참조)
- **공공데이터포털 API 키** 필요: `DATA_GO_KR_API_KEY` (.env에 설정)
- python-docx 설치 필요: `pip install python-docx>=1.1.0`
- reportlab 설치 필요: `pip install reportlab>=4.0.0`
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
```

## 주요 파일 (Post-2 신규/수정)
- `backend/app/data/env_standards.py` — 환경기준 데이터 (신규)
- `backend/app/services/standard_checker.py` — 기준 비교 서비스 (신규)
- `backend/app/schemas/standards.py` — 기준 비교 API 스키마 (신규)
- `backend/app/api/v1/standards.py` — 기준 비교 API 엔드포인트 (신규)
- `backend/app/services/draft_scaffold.py` — scaffold 기준 비교 반영 (수정)
- `backend/app/services/qa_engine.py` — R006 규칙 추가 (수정)
- `backend/app/main.py` — standards 라우터 등록 (수정)
- `backend/tests/test_standard_checker.py` — 테스트 27개 (신규)
