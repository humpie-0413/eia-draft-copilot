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

## Post-1: 데이터 전처리 및 통계 엔진 ✅

### 완료 항목
- 통계 서비스 (`backend/app/services/statistics.py`):
  - 섹션별/지표별 기술 통계 계산 (평균, 최대, 최소, 표준편차, 건수, 기간)
  - numeric_value 있는 본 평가(screening_only=False) 데이터만 대상
  - 카테고리별 기본 연도 필터 (수질 5년, 대기 1년)
  - 일평균 집계 옵션 (시간별 데이터 → 일평균)
  - observed_at NULL 데이터 시간필터에서 보존
- 통계 API 엔드포인트:
  - GET /projects/{id}/statistics — 전체 섹션 통계
  - GET /projects/{id}/statistics/{section_key} — 개별 섹션 통계
  - 쿼리 파라미터: years_filter (0=전체, N=최근N년, 미지정=기본값), aggregate_daily
- scaffold 서비스 수정:
  - 기존 개별 측정값 나열 → 지표별 1행 통계 요약 테이블로 변경
  - 비수치 데이터 별도 섹션 분리 표시
  - 상세 데이터는 부록으로 이동 (최대 10건 샘플)
- 테스트 16개 (`backend/tests/test_statistics.py`)

### 주요 파일
- `backend/app/services/statistics.py` — 통계 계산 서비스
- `backend/app/schemas/statistics.py` — 통계 API 응답 스키마
- `backend/app/api/v1/statistics.py` — 통계 API 엔드포인트
- `backend/app/services/draft_scaffold.py` — scaffold 요약문 통계 방식 전환
- `backend/tests/test_statistics.py` — 통계 테스트 16개

### 커밋
- `e57db3a` — feat: 통계 서비스 및 API 엔드포인트 추가 (Post-1)
- `2047700` — refactor: scaffold 요약문을 통계 테이블 방식으로 변경 (Post-1)
- `aa47d9b` — test: Post-1 통계 엔진 테스트 16개 추가
- `e988232` — fix: 시간필터 적용 시 observed_at이 NULL인 데이터 보존

---

## Post-2: 환경기준 비교 엔진 ✅

### 완료 항목
- 환경기준 데이터 정의 (`backend/app/data/env_standards.py`):
  - 대기환경기준 (PM10, PM2.5, SO2, NO2, CO, O3 — 연평균/24시간/1시간)
  - 수질환경기준 (하천 생활환경기준 Ia~V등급, BOD/COD/SS/DO/T-P)
  - 소음환경기준 (주거지역 주간 55dB, 야간 45dB)
  - 수질 등급 판정 함수 (BOD/COD/DO/T-P 기반 최악 등급 적용)
- 기준 비교 서비스 (`backend/app/services/standard_checker.py`):
  - 통계 결과 ↔ 환경기준 비교 (적합/초과/해당없음 판정)
  - 수질 등급 판정 포함
  - 섹션별 기준 비교 요약 서술문 자동 생성
- 기준 비교 API:
  - GET /projects/{id}/standards-check — 전체 섹션 기준 비교
  - GET /projects/{id}/standards-check/{section_key} — 개별 섹션
- scaffold 서비스 수정:
  - 통계 요약 테이블에 "환경기준" 및 "판정" 열 추가
  - 기준 비교 서술문 섹션 추가
- QA 규칙 R006: 환경기준 초과 지표 warning (초과 지표명 + 수치 포함)
- 테스트 27개 (`backend/tests/test_standard_checker.py`)
  - 대기/수질/소음 적합·초과 판정 테스트 9개
  - API 테스트 3개
  - scaffold 서술문 테스트 5개
  - R006 QA 규칙 테스트 4개
  - 순수 함수 단위 테스트 6개

### 주요 파일
- `backend/app/data/env_standards.py` — 환경기준 데이터 (신규)
- `backend/app/services/standard_checker.py` — 기준 비교 서비스 (신규)
- `backend/app/schemas/standards.py` — 기준 비교 API 스키마 (신규)
- `backend/app/api/v1/standards.py` — 기준 비교 API 엔드포인트 (신규)
- `backend/app/services/draft_scaffold.py` — scaffold 기준 비교 반영 (수정)
- `backend/app/services/qa_engine.py` — R006 규칙 추가 (수정)
- `backend/app/main.py` — standards 라우터 등록 (수정)
- `backend/tests/test_standard_checker.py` — 테스트 27개 (신규)

### 커밋
- `0f524a4` — feat: 환경기준 비교 엔진 구현 (Post-2)

---

## Post-3: 초안 텍스트 생성기 고도화 ✅

### 완료 항목
- 서술문 템플릿 엔진 (`backend/app/services/narrative_generator.py`):
  - 대기질: 지표별 환경기준 비교 서술 + 초과 시 저감대책 언급
  - 수질: BOD/COD 병합 서술 + 등급 판정 + 기타 지표 서술
  - 소음·진동: 주간/야간 판정 + 진동 + 방음대책 서술
  - 생태: 식물상/동물상 종수 + 녹지자연도 + 법정보호종 서술
  - 범용: 토양/교통/폐기물 등 환경기준 없는 섹션
  - 미수집: "현장조사 및 자료 수집이 필요하다" 고정 서술문
  - LLM 미사용 결정적 템플릿 방식
- scaffold 서비스 전면 개편:
  - narrative 필드 분리 (서술문 ↔ 통계 요약 분리)
  - 상세 데이터 샘플 5건 제한 (나머지는 "별첨 참조")
  - summary_text: 측정 현황 요약 테이블 + 비수치 데이터 + 샘플
- DOCX/PDF export 4부 구조 개편:
  - 가. 현황 및 영향 분석 (서술문 본문)
  - 나. 측정 현황 요약 (통계 테이블)
  - 다. 환경기준 비교 (기준 비교 테이블)
  - 라. 측정 데이터 (대표 샘플 5건 + "별첨 참조")
  - 초과 지표 빨간색 표시
- API 스키마/엔드포인트 narrative 필드 추가
- 프론트엔드 초안 뼈대 화면 업데이트:
  - 서술문 미리보기 영역 (좌측 강조 바 스타일)
  - 원시 데이터 목록 접기/펼치기(collapsible) 전환
  - SectionStatusCard 확장 상태 색상 추가

### 테스트
- `backend/tests/test_narrative_generator.py`: 28개 신규 테스트
  - 미수집 섹션 3개, 대기질 4개, 수질 3개, 소음·진동 3개, 생태 3개
  - 범용 2개, 디스패처 4개, scaffold 통합 3개, DOCX 구조 3개
- 기존 테스트 Post-3 포맷 대응 수정
- PDF 테스트 project_type 수정 (energy → power_plant)
- 전체 136개 테스트 통과

### 주요 파일
- `backend/app/services/narrative_generator.py` — 서술문 템플릿 엔진 (신규)
- `backend/app/services/draft_scaffold.py` — scaffold 전면 개편 (수정)
- `backend/app/services/export_service.py` — DOCX/PDF 4부 구조 (수정)
- `backend/app/schemas/section.py` — narrative 필드 추가 (수정)
- `backend/app/api/v1/sections.py` — narrative 매핑 추가 (수정)
- `backend/tests/test_narrative_generator.py` — 테스트 28개 (신규)
- `src/types/section.ts` — narrative 필드 추가 (수정)
- `src/components/section/scaffold-section-view.tsx` — 서술문 UI (수정)
- `src/components/section/section-status-card.tsx` — 상태 색상 (수정)

### 커밋
- `9d52473` — feat: 서술문 템플릿 엔진 및 scaffold/export 4부 구조 개편 (Post-3)
- `262fe9d` — feat: 프론트엔드 초안 뼈대 화면 업데이트 (Post-3)

---

## Post-4: 추가 커넥터 (토양, 기후) + 수동 입력 가이드 ✅

### 완료 항목

#### 토양측정망 커넥터 (`backend/app/connectors/soil_info.py`)
- 국립환경과학원 토양측정망 정보 조회 API 연동
- Cd(카드뮴), Cu(구리), Pb(납), Zn(아연), Ni(니켈), Cr6+(6가크롬), pH, 유기물함량 8개 지표
- DATA_GO_KR_API_KEY 공유 사용
- 연도별·측정지점별 조회, 다양한 날짜 형식 지원

#### 기상청 ASOS 커넥터 (`backend/app/connectors/kma_weather.py`)
- 기상청 지상(종관, ASOS) 일자료 조회서비스 API 연동
- 평균기온, 최고기온, 최저기온, 강수량, 평균풍속, 최대풍속, 평균습도 7개 지표
- 관측소 번호 + 기간(YYYYMMDD) 기반 조회
- items.item 중첩 구조 및 직접 리스트 형태 모두 처리

#### 수동 입력 가이드 강화
- 10개 분야(토지이용, 교통, 폐기물, 경관, 문화재, 토양, 기후, 소음·진동, 생태 등) 권장 지표 안내
- 클릭 시 지표명 자동 입력, 데이터 출처 힌트 제공
- 커넥터 자동 수집 가능 분야는 별도 안내

#### 프론트엔드 업데이트
- 데이터 수집 다이얼로그에 토양/기후 커넥터 파라미터 추가
- 수동 추가 폼에 섹션별 권장 지표 안내 UI

#### 기타
- `.env.example` 파일 추가 (4개 커넥터 API 키 안내)
- 실제 API 연동 검증 스크립트에 토양/기후 테스트 추가

### 테스트
- 토양측정망 커넥터 단위 테스트 12개 (normalize 8개 + fetch 4개)
- 기상청 ASOS 커넥터 단위 테스트 13개 (normalize 8개 + fetch 5개)
- 레지스트리 테스트 업데이트 (4개 커넥터 확인)
- 커넥터 목록 API 테스트 업데이트
- 전체 161개 테스트 통과

### 주요 파일
- `backend/app/connectors/soil_info.py` — 토양측정망 커넥터 (신규)
- `backend/app/connectors/kma_weather.py` — 기상청 ASOS 커넥터 (신규)
- `backend/app/connectors/registry.py` — 4개 커넥터 등록 (수정)
- `backend/tests/test_connectors.py` — 25개 테스트 추가 (수정)
- `scripts/test_connectors_live.py` — 토양/기후 검증 추가 (수정)
- `src/components/evidence/evidence-form-dialog.tsx` — 권장 지표 안내 (수정)
- `src/components/evidence/collect-data-dialog.tsx` — 커넥터 파라미터 (수정)
- `backend/.env.example` — 환경변수 예제 (신규)

### 커밋
- `9c5918c` — feat: 토양측정망 + 기상청 ASOS 커넥터 구현 (Post-4)
- `41b835b` — feat: 수동 입력 가이드 + 커넥터 UI 업데이트 (Post-4)
- `2a4e488` — docs: .env.example 추가 — 4개 커넥터 API 키 안내 (Post-4)

---

## 전체 커밋 이력 (48건)

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
| 39 | `e57db3a` | feat: 통계 서비스 및 API 엔드포인트 추가 (Post-1) |
| 40 | `2047700` | refactor: scaffold 요약문을 통계 테이블 방식으로 변경 (Post-1) |
| 41 | `aa47d9b` | test: Post-1 통계 엔진 테스트 16개 추가 |
| 42 | `e988232` | fix: 시간필터 적용 시 observed_at이 NULL인 데이터 보존 |
| 43 | `0f524a4` | feat: 환경기준 비교 엔진 구현 (Post-2) |
| 44 | `9d52473` | feat: 서술문 템플릿 엔진 및 scaffold/export 4부 구조 개편 (Post-3) |
| 45 | `262fe9d` | feat: 프론트엔드 초안 뼈대 화면 업데이트 (Post-3) |
| 46 | `9c5918c` | feat: 토양측정망 + 기상청 ASOS 커넥터 구현 (Post-4) |
| 47 | `41b835b` | feat: 수동 입력 가이드 + 커넥터 UI 업데이트 (Post-4) |
| 48 | `2a4e488` | docs: .env.example 추가 — 4개 커넥터 API 키 안내 (Post-4) |
