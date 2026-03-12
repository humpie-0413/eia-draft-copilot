# Next Chat Brief

## 마지막 완료 Phase
**Phase 6: QA 규칙 엔진 + Export Gate + DOCX 출력** ✅ (MVP 완료)

## 완료된 작업 (Phase 6)

### 백엔드
- QA 규칙 엔진 서비스 (`backend/app/services/qa_engine.py`):
  - 5개 결정적 규칙 (R001~R005)
  - R001: 섹션 증거 없음 (핵심 섹션=critical, 기타=warning)
  - R002: 필수 지표 누락 검사
  - R003: 충족도 50% 미만 경고
  - R004: 근거 없는 완료 상태 (unsupported claim) 검출
  - R005: 단일 근거 지표 정보 제공
  - 심각도 등급: critical / warning / info
  - export_ready 판정: critical 이슈 없으면 True
- Pydantic 스키마 (`backend/app/schemas/qa.py`):
  - QaIssueRead, QaSummaryRead, QaResultRead, ExportReadyRead
- QA API 엔드포인트 (`backend/app/api/v1/qa.py`):
  - GET `/projects/{id}/qa` — QA 실행 결과 반환
  - GET `/projects/{id}/qa/export-ready` — export 가능 여부 간략 확인
- DOCX 출력 서비스 (`backend/app/services/export_service.py`):
  - python-docx 기반 DOCX 문서 생성
  - 표지 페이지 (프로젝트명, 생성일)
  - 목차 페이지 (섹션별 근거 상태)
  - 섹션별 내용: 현황 요약 + 근거 데이터 테이블 (4열)
  - Export Gate: critical QA 이슈 시 export 차단 (ValueError)
- Export API 엔드포인트 (`backend/app/api/v1/export.py`):
  - POST `/projects/{id}/export/docx` — DOCX 다운로드 (StreamingResponse)
  - 422 에러 시 critical 이슈 미해결 안내

### 프론트엔드
- TypeScript 타입 (`src/types/qa.ts`):
  - QaIssue, QaSummary, QaResult, ExportReady
  - SEVERITY_LABELS, SEVERITY_COLORS 상수
- API 클라이언트 (`src/lib/qa-api.ts`):
  - getQaResult, checkExportReady, downloadDocx
- 컴포넌트:
  - QaIssueList — 이슈 카드 목록 (아이콘 · 뱃지 · 심각도 필터링)
  - QaSummaryBar — 심각도별 카운트 + export 가능 여부 표시
  - ExportButton — DOCX 다운로드 (QA 통과 시만 활성)
- 페이지:
  - `/projects/[id]/qa` — QA 결과 페이지 (재검사, 심각도 탭, 이슈 목록, export)
- 기존 페이지 수정:
  - 초안 뼈대 페이지: QA 요약 바 + Export 버튼 + QA 검사 링크 추가
  - 프로젝트 목록: QA / Export 버튼 추가

## 이전 완료 Phase
- Phase 0: 스캐폴딩 ✅
- Phase 1: Project CRUD & Backend API ✅
- Phase 2: 데이터 커넥터 & Evidence 인프라 ✅
- Phase 3: Evidence Workbench UI ✅
- Phase 4: 유사사례 매칭 시스템 ✅
- Phase 5: 섹션 플래너 + 초안 뼈대 ✅

## MVP 완료 상태
Phase 0~6까지 구현 완료. 핵심 워크플로우:
1. 프로젝트 생성 → 2. 증거 수집 → 3. 유사사례 매칭 → 4. 섹션 플래너 → 5. 초안 뼈대 → 6. QA 검사 → 7. DOCX 출력

## 향후 작업 (Phase 7+)
- Vercel 배포 설정
- 사용자 인증 (NextAuth.js)
- AI 연동 (Claude API) — 섹션별 프롬프트 + 스트리밍 응답
- 커넥터 실제 API 호출 구현 (httpx 기반)
- 성능 최적화 및 에러 핸들링

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`.env.example` 참조)
- python-docx 설치 필요: `pip install python-docx>=1.1.0`
- 커넥터 fetch()는 NotImplementedError — 실제 API 키 및 호출 로직은 미구현
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
```

## 주요 파일
### Phase 6 신규 파일
- `backend/app/services/qa_engine.py` — QA 규칙 엔진
- `backend/app/services/export_service.py` — DOCX 출력 서비스
- `backend/app/schemas/qa.py` — QA Pydantic 스키마
- `backend/app/api/v1/qa.py` — QA API 엔드포인트
- `backend/app/api/v1/export.py` — Export API 엔드포인트
- `src/types/qa.ts` — TypeScript QA 타입
- `src/lib/qa-api.ts` — QA/Export API 클라이언트
- `src/components/qa/qa-issue-list.tsx` — QA 이슈 목록 컴포넌트
- `src/components/qa/qa-summary-bar.tsx` — QA 요약 바 컴포넌트
- `src/components/qa/export-button.tsx` — Export 버튼 컴포넌트
- `src/app/projects/[id]/qa/page.tsx` — QA 결과 페이지

### 기존 파일 수정
- `backend/app/main.py` — qa, export 라우터 등록
- `backend/requirements.txt` — python-docx 추가
- `src/app/projects/[id]/draft/page.tsx` — QA 요약 + Export 버튼 통합
- `src/app/projects/page.tsx` — QA / Export 버튼 추가
