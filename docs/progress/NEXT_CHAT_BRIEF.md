# Next Chat Brief

## 마지막 완료 Phase
**Phase 3: Evidence Workbench UI (증거 작업대)** ✅

## 완료된 작업 (Phase 3)
- shadcn/ui 설치 및 설정 (CSS 변수 기반 green 테마, 12개 UI 컴포넌트)
- TypeScript 타입 정의: Evidence, EvidenceCategory, DataSource, SourceSnapshot, Project
- API 클라이언트: fetch 래퍼 (ApiError 클래스) + 증거 CRUD 함수 + 스냅샷 조회
- Evidence Workbench 페이지 (`/projects/[id]/evidences`):
  - EvidenceFilters: 분야 선택(Select) + screening_only 토글(Switch) + 초기화
  - EvidenceTable: 증거 목록 테이블 (분야 Badge, 본평가/스크리닝 구분, CRUD 버튼)
  - EvidenceDetailSheet: 증거 상세 사이드 시트 (메타데이터 + raw_payload 표시)
  - EvidenceFormDialog: 증거 수동 추가/편집 폼 (유효성 검사 포함)
  - 삭제 확인 다이얼로그
- 프로젝트 목록 페이지 (`/projects`) — 카드 UI + 증거 작업대 링크
- 홈페이지에 프로젝트 목록 이동 버튼 추가

## 다음 작업: Phase 3.5 이후
- Draft Editor UI (리치 텍스트 에디터, 섹션 네비게이션)
- AI 연동 (Claude API) — 섹션별 프롬프트 + 스트리밍 응답
- 커넥터 실제 API 호출 구현 (httpx 기반)
- 유사사례 검색, section planner

## 주의사항
- PostgreSQL + PostGIS 로컬 설치 필요
- `backend/.env` 설정 필요 (`.env.example` 참조)
- 커넥터 fetch()는 NotImplementedError — 실제 API 키 및 호출 로직은 미구현
- 마이그레이션 실행: `cd backend && alembic upgrade head`
- 프론트엔드 환경변수: `NEXT_PUBLIC_API_URL` (기본값 http://localhost:8000)

## 실행 방법
```bash
# 프론트엔드
npm run dev    # http://localhost:3000

# 백엔드
cd backend
uvicorn app.main:app --reload    # http://localhost:8000
```

## 주요 파일
### 프론트엔드 (신규)
- `src/types/evidence.ts` — Evidence 타입 + EVIDENCE_CATEGORIES 한글 매핑
- `src/types/project.ts` — Project 타입
- `src/types/api.ts` — API 공통 타입
- `src/lib/api-client.ts` — 공통 API 클라이언트
- `src/lib/evidence-api.ts` — 증거 API 함수
- `src/components/evidence/evidence-filters.tsx` — 필터 컴포넌트
- `src/components/evidence/evidence-table.tsx` — 테이블 컴포넌트
- `src/components/evidence/evidence-detail-sheet.tsx` — 상세 시트
- `src/components/evidence/evidence-form-dialog.tsx` — 추가/편집 폼
- `src/app/projects/[id]/evidences/page.tsx` — Evidence Workbench 페이지
- `src/app/projects/page.tsx` — 프로젝트 목록 페이지
- `src/components/ui/` — shadcn/ui 컴포넌트 (12개)

### 백엔드 (Phase 2에서 구현)
- `backend/app/api/v1/evidences.py` — Evidence API 엔드포인트
- `backend/app/api/v1/snapshots.py` — Snapshot API 엔드포인트
- `backend/app/schemas/evidence.py` — Evidence 스키마 + EvidenceCategory enum
- `backend/app/crud/evidence.py` — Evidence CRUD 함수
