# Work Log

## Phase 0: 프로젝트 스캐폴딩 및 기획 ✅

### 완료 항목
- Git 저장소 클론 (`https://github.com/humpie-0413/eia-draft-copilot.git`)
- 디렉토리 구조 생성: `src/app`, `src/components`, `src/lib`, `src/types`, `docs/`
- `CLAUDE.md` 작성 — 프로젝트 개요, 기술 스택 (Next.js 14 + TS + Tailwind), 컨벤션
- `docs/claude/phase-plan.md` 작성 — Phase 0~5 전체 로드맵
- `docs/progress/NEXT_CHAT_BRIEF.md` 작성 — 다음 세션 인수인계
- Next.js + TypeScript + Tailwind CSS 프로젝트 초기화 (`package.json`, `tsconfig.json`)
- 기본 레이아웃 (`layout.tsx`) 및 랜딩 페이지 (`page.tsx`) 생성
- 설정 파일: `.eslintrc.json`, `postcss.config.js`, `tailwind.config.ts`, `.gitignore`, `.env.example`
- `npm run build` 성공 확인
- `npx next lint` 통과 확인

### 커밋
- `be6ff2d` — init
- `de9f1e0` — chore: Phase 0 — project scaffolding and planning
- `4c6c69f` — docs: add WORKLOG.md and smoke test for Phase 0 checkpoint

---

## Phase 1: Project CRUD & Backend API ✅

### 완료 항목
- FastAPI 백엔드 스캐폴딩 (`backend/`)
- PostgreSQL + PostGIS DB 스키마 (projects 테이블)
- Alembic 마이그레이션 설정 및 초기 마이그레이션 001
- Project CRUD API 엔드포인트 (POST/GET/PATCH/DELETE)
- GeoJSON 지오메트리 입력 및 검증 (geojson-pydantic)
- Pydantic v2 스키마 기반 입력 검증 및 에러 핸들링
- 통합 테스트 (pytest + httpx)

### 주요 파일
- `backend/app/main.py` — FastAPI 앱 엔트리포인트
- `backend/app/config.py` — 환경 설정 (pydantic-settings)
- `backend/app/db.py` — SQLAlchemy async 세션 관리
- `backend/app/models/project.py` — Project 모델 (PostGIS geometry)
- `backend/app/schemas/project.py` — 프로젝트 Pydantic 스키마
- `backend/app/crud/project.py` — 프로젝트 CRUD 함수
- `backend/app/api/v1/projects.py` — 프로젝트 API 엔드포인트
- `backend/alembic/versions/001_create_projects.py` — 초기 마이그레이션
- `backend/tests/test_projects.py` — 프로젝트 테스트

### 커밋
- `1ad12aa` — feat: Phase 1 — Project CRUD API with PostGIS geometry

---

## Phase 2: 공공데이터 커넥터 & Evidence 인프라 ✅

### 완료 항목
- data_sources 테이블 및 스키마 (소스 레지스트리)
- source_snapshots 테이블 및 스키마 (raw payload JSONB 보존)
- evidences 테이블 및 스키마 (정규화된 증거 + screening_only 분리)
- Alembic 마이그레이션 002 (3개 테이블 + 인덱스)
- CRUD 함수 (벌크 생성, 필터 조회 포함)
- REST API 엔드포인트 (data-sources, evidences, snapshots)
- BaseConnector 추상 클래스 + 레지스트리
- 커넥터 스켈레톤: KecoAirConnector (대기질), WaterInfoConnector (수질)

### 주요 파일
- `backend/app/models/data_source.py` — DataSource 모델
- `backend/app/models/source_snapshot.py` — SourceSnapshot 모델
- `backend/app/models/evidence.py` — Evidence 모델 (PostGIS location)
- `backend/app/schemas/evidence.py` — Evidence 스키마 (12개 카테고리)
- `backend/app/schemas/data_source.py` — DataSource 스키마
- `backend/app/schemas/source_snapshot.py` — Snapshot 스키마
- `backend/app/crud/evidence.py` — Evidence CRUD (벌크 포함)
- `backend/app/crud/data_source.py` — DataSource CRUD
- `backend/app/crud/source_snapshot.py` — Snapshot CRUD
- `backend/app/api/v1/evidences.py` — Evidence API
- `backend/app/api/v1/data_sources.py` — DataSource API
- `backend/app/api/v1/snapshots.py` — Snapshot API
- `backend/app/connectors/base.py` — BaseConnector 추상 클래스
- `backend/app/connectors/registry.py` — 커넥터 레지스트리
- `backend/app/connectors/keco_air.py` — 에어코리아 커넥터 스켈레톤
- `backend/app/connectors/water_info.py` — 수질 커넥터 스켈레톤
- `backend/alembic/versions/002_create_evidence_tables.py` — 마이그레이션

### 커밋
- `f5707bd` — feat: Phase 2 — data_source, source_snapshot, evidence 모델 및 스키마 추가
- `11cf956` — feat: Alembic 002 마이그레이션 — 증거 수집 테이블 생성
- `aaf556a` — feat: data_source, source_snapshot, evidence CRUD 함수 추가
- `34a3894` — feat: 공공데이터 커넥터 스켈레톤 구현
- `46c79e4` — feat: data_source, evidence, snapshot REST API 엔드포인트 추가
- `8dbf134` — docs: Phase 2 완료 — 문서 업데이트

---

## Phase 3: Evidence Workbench UI ✅

### 완료 항목
- shadcn/ui 설치 및 기본 설정 (Radix UI + Tailwind CSS 테마)
- TypeScript 타입 정의 (Evidence, Project, DataSource, SourceSnapshot)
- API 클라이언트 (fetch 래퍼 + 증거/스냅샷 API 함수)
- 프로젝트별 증거 목록 조회/필터링 화면 (`/projects/[id]/evidences`)
- 증거 상세 보기 (메타데이터 + raw_payload 원시 데이터 확인)
- screening_only 토글 필터 + 분야별 필터 (12개 카테고리)
- 증거 수동 추가/편집 폼 (다이얼로그)
- 증거 삭제 확인 다이얼로그
- 프로젝트 목록 페이지 (`/projects`)

### 주요 파일
- `src/types/evidence.ts` — Evidence 타입 + 12개 카테고리 상수
- `src/types/project.ts` — Project 타입
- `src/types/api.ts` — 공통 API 타입 (PaginatedList)
- `src/lib/api-client.ts` — HTTP 클라이언트 래퍼
- `src/lib/evidence-api.ts` — Evidence API 함수
- `src/components/ui/` — shadcn/ui 컴포넌트 12개
- `src/components/evidence/evidence-table.tsx` — 증거 테이블
- `src/components/evidence/evidence-form-dialog.tsx` — 증거 폼
- `src/components/evidence/evidence-filters.tsx` — 필터 바
- `src/components/evidence/evidence-detail-sheet.tsx` — 상세 시트
- `src/app/projects/page.tsx` — 프로젝트 목록
- `src/app/projects/[id]/evidences/page.tsx` — Evidence Workbench

### 커밋
- `0bce767` — feat: shadcn/ui 설치 및 기본 설정
- `aa1e4d4` — feat: TypeScript 타입 정의 및 API 클라이언트 추가
- `42567d5` — feat: Evidence Workbench UI 구현
- `db16cbe` — docs: Phase 3 완료 — 문서 업데이트

---

## Phase 4: 유사사례 매칭 시스템 ✅

### 완료 항목
- SimilarCase 모델 + Alembic 마이그레이션 003
- Pydantic 스키마 (CRUD + 매칭 결과 SimilarCaseMatchResult)
- CRUD 함수 (생성/조회/목록/수정/삭제)
- 유사도 계산 서비스 (사업유형 35% / 위치 25% / 규모 20% / 환경분야 20% 가중 평균)
- API 엔드포인트: CRUD + 매칭 검색 (GET /similar-cases/match/{project_id})
- 기존 evidence/geometry 데이터 연계 (환경 분야 자동 추출, ST_Area 면적 추정)
- 프론트엔드: 매칭 결과 테이블, 상세 시트, 유사사례 페이지

### 주요 파일
- `backend/app/models/similar_case.py` — SimilarCase 모델
- `backend/app/schemas/similar_case.py` — 유사사례 스키마
- `backend/app/crud/similar_case.py` — 유사사례 CRUD
- `backend/app/services/similarity.py` — 유사도 계산 서비스
- `backend/app/api/v1/similar_cases.py` — 유사사례 API
- `backend/alembic/versions/003_create_similar_cases.py` — 마이그레이션
- `src/types/similar-case.ts` — 유사사례 TypeScript 타입
- `src/lib/similar-case-api.ts` — 유사사례 API 클라이언트
- `src/components/similar-case/similar-case-match-table.tsx` — 매칭 테이블
- `src/components/similar-case/similar-case-detail-sheet.tsx` — 상세 시트
- `src/app/projects/[id]/similar-cases/page.tsx` — 유사사례 페이지

### 커밋
- `383784b` — feat: 유사사례(SimilarCase) 모델, 스키마, Alembic 마이그레이션 추가
- `fbfab86` — feat: 유사사례 CRUD 함수 및 유사도 계산 서비스 구현
- `c0f762d` — feat: 유사사례 API 엔드포인트 및 매칭 검색 API 구현
- `4f8f301` — feat: 유사사례 프론트엔드 UI 구현
- `2af8723` — docs: Phase 4 완료 — NEXT_CHAT_BRIEF 및 phase-plan 업데이트

---

## Phase 5: 섹션 플래너 + 초안 뼈대 ✅

### 완료 항목
- 섹션 정의 서비스: EIA 11개 섹션 정의 (대기질, 수질, 토양, 소음·진동, 생태, 토지이용, 교통, 폐기물, 경관, 문화재, 기후)
- 섹션별 필수 지표 목록 + 충족도(coverage_ratio) 계산
- 섹션 상태 엔진: empty/partial/complete 판정
- 초안 뼈대 서비스: evidence 기반 근거 나열 방식 (unsupported claim 금지)
- Pydantic 스키마: 섹션 상태 + 초안 뼈대 응답 모델
- API 엔드포인트 5개 (definitions, status, status/{key}, scaffold, scaffold/{key})
- 프론트엔드: 섹션 플래너 페이지 (`/projects/[id]/sections`)
- 프론트엔드: 초안 뼈대 페이지 (`/projects/[id]/draft`)

### 주요 파일
- `backend/app/services/section_planner.py` — 섹션 정의 + 상태 계산
- `backend/app/services/draft_scaffold.py` — 초안 뼈대 생성
- `backend/app/schemas/section.py` — 섹션/초안 스키마
- `backend/app/api/v1/sections.py` — 섹션 API
- `src/types/section.ts` — 섹션 TypeScript 타입
- `src/lib/section-api.ts` — 섹션 API 클라이언트
- `src/components/section/section-status-card.tsx` — 섹션 상태 카드
- `src/components/section/scaffold-section-view.tsx` — 초안 섹션 뷰
- `src/app/projects/[id]/sections/page.tsx` — 섹션 플래너
- `src/app/projects/[id]/draft/page.tsx` — 초안 뼈대

### 커밋
- `1ca5515` — feat: Phase 5 백엔드 — 섹션 플래너 및 초안 뼈대 서비스/API
- `0d32efe` — feat: Phase 5 프론트엔드 — 섹션 플래너 UI 및 초안 뼈대 뷰어
- `c4ae708` — docs: Phase 5 완료 문서 업데이트

---

## Phase 6: QA 규칙 엔진 + Export Gate + DOCX 출력 ✅ (MVP 완료)

### 완료 항목
- 결정적 QA 규칙 엔진 (5개 규칙)
  - R001: 섹션 증거 없음 (핵심 섹션 critical / 기타 warning)
  - R002: 필수 지표 누락 검사
  - R003: 충족도 50% 미만 경고
  - R004: 근거 없는 완료 상태 (unsupported claim) 검출
  - R005: 단일 근거 지표 정보 제공
- 심각도 등급: critical (export 차단) / warning / info
- QA 결과 API: GET /projects/{id}/qa, GET /projects/{id}/qa/export-ready
- Export Gate: critical 이슈 시 export 차단
- DOCX 출력 서비스 (python-docx): 표지 + 목차 + 섹션별 근거 테이블
- DOCX 다운로드 API: POST /projects/{id}/export/docx
- QA 결과 UI 페이지 (`/projects/[id]/qa`): 이슈 목록, 심각도 필터, export 버튼
- 초안 뼈대 페이지에 QA 요약 + Export 버튼 통합
- 프로젝트 목록에 QA / Export 버튼 추가

### 주요 파일
- `backend/app/services/qa_engine.py` — QA 규칙 엔진 (5개 규칙)
- `backend/app/services/export_service.py` — DOCX 생성 서비스
- `backend/app/schemas/qa.py` — QA 스키마
- `backend/app/api/v1/qa.py` — QA API
- `backend/app/api/v1/export.py` — Export API
- `src/types/qa.ts` — QA TypeScript 타입
- `src/lib/qa-api.ts` — QA/Export API 클라이언트
- `src/components/qa/qa-issue-list.tsx` — QA 이슈 목록
- `src/components/qa/qa-summary-bar.tsx` — QA 요약 바
- `src/components/qa/export-button.tsx` — Export 버튼
- `src/app/projects/[id]/qa/page.tsx` — QA 결과 페이지

### 커밋
- `ddb2a27` — feat: Phase 6 — 결정적 QA 규칙 엔진 백엔드
- `841ace5` — feat: Phase 6 — DOCX 출력 서비스 및 Export Gate
- `3115561` — feat: Phase 6 — QA/Export 프론트엔드 타입 및 API 클라이언트
- `43a5de6` — feat: Phase 6 — QA 결과 UI (컴포넌트 + 페이지)
- `5b205a7` — feat: Phase 6 — 초안 뼈대 페이지에 QA/Export 통합
- `dd0423b` — docs: Phase 6 완료 — 문서 업데이트

---

## E2E 테스트 및 버그 수정 ✅

### 완료 항목
- E2E 통합 테스트 추가 (`backend/tests/test_e2e.py`)
- 테스트 인프라 개선 (`conftest.py` 업데이트)
- E2E 검증에서 발견된 3건의 버그 수정

### 커밋
- `5903161` — fix: E2E 검증에서 발견된 3건의 버그 수정
- `a6bbe3b` — test: E2E 통합 테스트 추가 및 테스트 인프라 개선

---

## 커넥터 실제 API 연동 ✅

### 완료 항목

#### 백엔드
- 에어코리아 대기질 커넥터 (`backend/app/connectors/keco_air.py`):
  - 공공데이터포털 에어코리아 대기오염정보 API 실제 연동 (httpx)
  - PM10, PM2.5, O3, NO2, SO2, CO 6개 지표 수집
  - API 키 환경변수 처리 (DATA_GO_KR_API_KEY)
  - fetch → raw_payload 스냅샷 저장 → normalize → evidence 벌크 저장
  - 에러 처리 (API 키 미설정, 측정소명 누락, API 오류 응답, 통신장애 값)
- 물환경정보시스템 수질 커넥터 (`backend/app/connectors/water_info.py`):
  - 국립환경과학원 수질측정정보 API 실제 연동 (httpx)
  - BOD, COD, SS, DO, T-N, T-P 6개 지표 수집
  - 측정지점별·기간별 조회
  - YYYYMMDD 날짜 변환, 빈 값/None 건너뛰기
- 커넥터 수집 API (`backend/app/api/v1/connectors.py`):
  - GET /connectors — 커넥터 목록
  - POST /connectors/{connector_key}/collect — 수집 실행
  - 데이터 소스 자동 등록
- Pydantic 스키마 (`backend/app/schemas/connector.py`):
  - CollectRequest, CollectResult
- 환경 설정 (`backend/app/config.py`):
  - DATA_GO_KR_API_KEY, CONNECTOR_TIMEOUT 설정 추가

#### 프론트엔드
- TypeScript 타입 (`src/types/connector.ts`): ConnectorInfo, CollectRequest, CollectResult
- API 클라이언트 (`src/lib/connector-api.ts`): listConnectors, collectData
- 데이터 수집 다이얼로그 (`src/components/evidence/collect-data-dialog.tsx`)
- Evidence Workbench에 "데이터 수집" 버튼 추가

#### 테스트
- 커넥터 연동 테스트 27개 (`backend/tests/test_connectors.py`)
- 커넥터 실제 API 연동 검증 스크립트 (`scripts/test_connectors_live.py`)

### 커밋
- `65d0bdc` — feat: 에어코리아 대기질 · 물환경정보 수질 커넥터 실제 API 연동
- `1224db0` — feat: 커넥터 수집 실행 API 엔드포인트 추가
- `9bc22d6` — test: 커넥터 연동 테스트 27개 추가
- `c37320a` — feat: 프론트엔드 데이터 수집 연동
- `3380939` — docs: 커넥터 실제 연동 완료 — 문서 업데이트

---

## 커넥터 변경 및 최종 검증 ✅

### 완료 항목
- .env에 OPENAI_API_KEY, GOOGLE_API_KEY 설정 추가 (향후 LLM 연동 대비)
- 수질 커넥터 API를 국립환경과학원 수질 DB(WaterQualityService)로 변경
- 커넥터 실제 API 연동 검증 스크립트 추가

### 커밋
- `649a5fa` — feat: .env에 OPENAI_API_KEY, GOOGLE_API_KEY 설정 추가
- `c071872` — feat: 수질 커넥터 API를 국립환경과학원 수질 DB로 변경
- `2f27ed4` — test: 커넥터 실제 API 연동 검증 스크립트 추가

---

## 전체 커밋 이력 (38건)

| # | 해시 | 메시지 |
|---|------|--------|
| 1 | `be6ff2d` | init |
| 2 | `de9f1e0` | chore: Phase 0 — project scaffolding and planning |
| 3 | `4c6c69f` | docs: add WORKLOG.md and smoke test for Phase 0 checkpoint |
| 4 | `1ad12aa` | feat: Phase 1 — Project CRUD API with PostGIS geometry |
| 5 | `f5707bd` | feat: Phase 2 — data_source, source_snapshot, evidence 모델 및 스키마 추가 |
| 6 | `11cf956` | feat: Alembic 002 마이그레이션 — 증거 수집 테이블 생성 |
| 7 | `aaf556a` | feat: data_source, source_snapshot, evidence CRUD 함수 추가 |
| 8 | `34a3894` | feat: 공공데이터 커넥터 스켈레톤 구현 |
| 9 | `46c79e4` | feat: data_source, evidence, snapshot REST API 엔드포인트 추가 |
| 10 | `8dbf134` | docs: Phase 2 완료 — 문서 업데이트 |
| 11 | `0bce767` | feat: shadcn/ui 설치 및 기본 설정 |
| 12 | `aa1e4d4` | feat: TypeScript 타입 정의 및 API 클라이언트 추가 |
| 13 | `42567d5` | feat: Evidence Workbench UI 구현 |
| 14 | `db16cbe` | docs: Phase 3 완료 — 문서 업데이트 |
| 15 | `383784b` | feat: 유사사례(SimilarCase) 모델, 스키마, Alembic 마이그레이션 추가 |
| 16 | `fbfab86` | feat: 유사사례 CRUD 함수 및 유사도 계산 서비스 구현 |
| 17 | `c0f762d` | feat: 유사사례 API 엔드포인트 및 매칭 검색 API 구현 |
| 18 | `4f8f301` | feat: 유사사례 프론트엔드 UI 구현 |
| 19 | `2af8723` | docs: Phase 4 완료 — NEXT_CHAT_BRIEF 및 phase-plan 업데이트 |
| 20 | `1ca5515` | feat: Phase 5 백엔드 — 섹션 플래너 및 초안 뼈대 서비스/API |
| 21 | `0d32efe` | feat: Phase 5 프론트엔드 — 섹션 플래너 UI 및 초안 뼈대 뷰어 |
| 22 | `c4ae708` | docs: Phase 5 완료 문서 업데이트 |
| 23 | `ddb2a27` | feat: Phase 6 — 결정적 QA 규칙 엔진 백엔드 |
| 24 | `841ace5` | feat: Phase 6 — DOCX 출력 서비스 및 Export Gate |
| 25 | `3115561` | feat: Phase 6 — QA/Export 프론트엔드 타입 및 API 클라이언트 |
| 26 | `43a5de6` | feat: Phase 6 — QA 결과 UI (컴포넌트 + 페이지) |
| 27 | `5b205a7` | feat: Phase 6 — 초안 뼈대 페이지에 QA/Export 통합 |
| 28 | `dd0423b` | docs: Phase 6 완료 — 문서 업데이트 |
| 29 | `5903161` | fix: E2E 검증에서 발견된 3건의 버그 수정 |
| 30 | `a6bbe3b` | test: E2E 통합 테스트 추가 및 테스트 인프라 개선 |
| 31 | `65d0bdc` | feat: 에어코리아 대기질 · 물환경정보 수질 커넥터 실제 API 연동 |
| 32 | `1224db0` | feat: 커넥터 수집 실행 API 엔드포인트 추가 |
| 33 | `9bc22d6` | test: 커넥터 연동 테스트 27개 추가 |
| 34 | `c37320a` | feat: 프론트엔드 데이터 수집 연동 |
| 35 | `3380939` | docs: 커넥터 실제 연동 완료 — 문서 업데이트 |
| 36 | `649a5fa` | feat: .env에 OPENAI_API_KEY, GOOGLE_API_KEY 설정 추가 |
| 37 | `c071872` | feat: 수질 커넥터 API를 국립환경과학원 수질 DB로 변경 |
| 38 | `2f27ed4` | test: 커넥터 실제 API 연동 검증 스크립트 추가 |
