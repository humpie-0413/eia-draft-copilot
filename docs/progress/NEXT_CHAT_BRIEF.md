# Next Chat Brief

## 마지막 완료 작업
**PDF 출력 기능 + 실사용 시나리오 데모** ✅

## 완료된 작업 (PDF 출력 + 데모)

### PDF 출력 기능
- 백엔드 PDF 생성 서비스 (`backend/app/services/export_service.py`):
  - reportlab 기반 PDF 문서 생성 (한글 폰트 지원: 맑은 고딕/나눔고딕)
  - 문서 구조: 표지 → 목차 → 섹션별 요약문 + 근거 데이터 테이블
  - Export Gate 동일 적용 (critical QA 이슈 시 차단)
- API: `GET /api/v1/projects/{id}/export/pdf`
- 프론트엔드 (`src/components/qa/export-button.tsx`):
  - DOCX/PDF 선택 드롭다운 메뉴 추가
  - `downloadPdf()` API 클라이언트 함수 추가
- 테스트 (`backend/tests/test_export_pdf.py`):
  - PDF export 성공/차단/404/내용 검증 4개 테스트
  - E2E 테스트에 PDF 단계 추가
- `backend/requirements.txt`: `reportlab>=4.0.0` 추가

### 실사용 시나리오 데모 스크립트
- `scripts/demo_full_scenario.py`:
  - 시나리오: 강남구 태양광 발전소 환경영향평가
  - 7단계 전체 흐름: 프로젝트 생성 → 데이터 수집 → 유사사례 매칭 → 섹션 플래너 → 초안 뼈대 → QA → DOCX/PDF Export
  - 커넥터 실패 시 수동 데이터로 자동 대체 (폴백)
  - 결과 파일 `output/` 디렉토리에 저장

## 이전 완료 Phase
- Phase 0: 스캐폴딩 ✅
- Phase 1: Project CRUD & Backend API ✅
- Phase 2: 데이터 커넥터 & Evidence 인프라 ✅
- Phase 3: Evidence Workbench UI ✅
- Phase 4: 유사사례 매칭 시스템 ✅
- Phase 5: 섹션 플래너 + 초안 뼈대 ✅
- Phase 6: QA 규칙 엔진 + Export Gate + DOCX/PDF 출력 ✅ (MVP 완료)

## 향후 작업 (Phase 7+)
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

# 데모 실행 (백엔드 서버 실행 후)
python scripts/demo_full_scenario.py
```

## 주요 파일
### PDF 출력 신규/수정 파일
- `backend/app/services/export_service.py` — PDF 생성 서비스 (generate_pdf 추가)
- `backend/app/api/v1/export.py` — PDF export 엔드포인트 추가
- `backend/requirements.txt` — reportlab 추가
- `backend/tests/test_export_pdf.py` — PDF 테스트 4개
- `src/components/qa/export-button.tsx` — DOCX/PDF 선택 드롭다운
- `src/lib/qa-api.ts` — downloadPdf 함수 추가

### 데모 스크립트
- `scripts/demo_full_scenario.py` — 전체 흐름 데모 (7단계)
