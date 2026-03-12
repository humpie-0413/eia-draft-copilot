# Next Chat Brief

## 마지막 완료 작업
**Post-1: 데이터 전처리 및 통계 엔진** ✅

## 완료된 작업 (Post-1)

### 통계 서비스
- `backend/app/services/statistics.py`:
  - 섹션별/지표별 기술 통계 계산 (평균, 최대, 최소, 표준편차, 건수, 기간)
  - numeric_value 있는 본 평가(screening_only=False) 데이터만 대상
  - 카테고리별 기본 연도 필터 (수질 5년, 대기 1년)
  - 일평균 집계 옵션 (시간별 데이터 → 일평균)
  - observed_at NULL 데이터는 시간필터에서 보존 (날짜 미상 데이터 유지)

### 통계 API
- `GET /api/v1/projects/{id}/statistics` — 전체 섹션 통계
- `GET /api/v1/projects/{id}/statistics/{section_key}` — 개별 섹션 통계
- 쿼리 파라미터:
  - `years_filter`: 0=전체 기간, N=최근 N년, 미지정=카테고리별 기본값
  - `aggregate_daily`: true=일평균 집계, false=원본 그대로

### scaffold 서비스 수정
- 기존 개별 측정값 나열 → 지표별 1행 통계 요약 테이블로 변경
- 비수치 데이터 별도 섹션 분리 표시
- 상세 데이터는 부록으로 이동 (최대 10건 샘플만 표시)

### 테스트
- `backend/tests/test_statistics.py`: 16개 테스트 전부 통과
- 기존 E2E 테스트 (`test_e2e.py`) 호환성 유지
- 기존 PDF 테스트 (`test_export_pdf.py`) 3건 실패는 Post-1 이전부터 존재하는 기존 문제

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

## 향후 작업 (Post-2+)
- Post-2: 환경기준 비교 서비스 (기준값 DB + 초과 여부 자동 판정)
- Vercel 배포 설정
- 사용자 인증 (NextAuth.js)
- AI 연동 (Claude API) — 섹션별 프롬프트 + 스트리밍 응답
- 성능 최적화 및 에러 핸들링

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

## 주요 파일 (Post-1 신규/수정)
- `backend/app/services/statistics.py` — 통계 계산 서비스 (신규)
- `backend/app/schemas/statistics.py` — 통계 API 응답 스키마 (신규)
- `backend/app/api/v1/statistics.py` — 통계 API 엔드포인트 (신규)
- `backend/app/services/draft_scaffold.py` — scaffold 요약문 통계 방식 전환 (수정)
- `backend/app/main.py` — statistics 라우터 등록 (수정)
- `backend/tests/test_statistics.py` — 통계 테스트 16개 (신규)
