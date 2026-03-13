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

## Post-5: 문서 포맷 고도화 ✅

### 완료 항목

#### DOCX 템플릿 전면 개편
- 표지 페이지: "환경영향평가서 초안" + 사업명 + 사업유형(한글) + 위치(geometry centroid) + 작성일 + "EIA Draft Copilot으로 작성"
- 목차: 테이블 형태 — 섹션 번호("제N장") + 제목 + 충족도 상태(완료/미비/미수집) + 증거 건수
- 머리말: 사업명(좌측) + "환경영향평가서 초안"(우측) + 하단 구분선
- 꼬리말: 페이지 번호 필드(중앙) + 상단 구분선
- 표지 섹션은 머리말/꼬리말 없음 (섹션 분리)
- 섹션 번호 체계: "제1장 대기질" → "1.1 현황 및 영향 분석" → "1.2 측정 현황 요약" → "1.3 환경기준 비교" → "1.4 측정 데이터"

#### 테이블 디자인 개선
- 헤더 행 배경색 연한 파란(#D6E4F0), 교차 행 배경(#F5F5F7)
- 환경기준 초과 시 해당 행 배경 연한 빨간색(#FDE0DC)
- 열 너비 자동 조정 (지표명 넓게, 수치 좁게)

#### 부록 구조 (3종)
- 부록 A: 상세 측정 데이터 (섹션별 최대 50건, 전체 건수 초과 시 안내)
- 부록 B: 유사사례 매칭 결과 (유사도 점수 테이블 + 개별 사례 요약)
- 부록 C: QA 검사 결과 (요약 통계 + 이슈 목록, critical 행 빨간 배경)

#### PDF 동일 적용
- reportlab 기반 PDF에도 동일한 표지/목차/머리말꼬리말/부록 구조
- onFirstPage / onLaterPages 콜백으로 머리말/꼬리말 렌더링
- 초과 행 빨간 배경, 헤더 색상, 교차 행 배경 동일 적용

#### API 변경
- Export 옵션 쿼리 파라미터: `include_appendix_a`, `include_appendix_b`, `include_appendix_c`
- GET /export/preview: 문서 구조 미리보기 엔드포인트 신규
- `generate_docx`/`generate_pdf` 시그니처 변경: Project 모델 직접 수신 + ExportOptions
- ExportContext 데이터 구조 도입 (scaffold + stats + check + similar + qa 통합)

#### 프론트엔드 개선
- ExportPreviewPanel: 문서 구조 트리 표시 (표지 → 목차 → 섹션들 → 부록)
  - 섹션별 상태 아이콘/색상 (완료=초록, 미비=노랑, 미수집=빨강)
  - 부록 A/B/C 포함 여부 체크박스 (옵션)
- ExportButton: 선택된 옵션을 쿼리 파라미터로 전달
- ExportOptions / ExportPreview 타입 정의

### 테스트
- `backend/tests/test_export_format.py`: 40개 신규 테스트
  - 유틸 함수 2개 (state_label, project_type_korean)
  - DOCX 표지 6개 (제목, 사업명, 사업유형, centroid, 날짜, 라벨)
  - DOCX 목차 4개 (테이블, 섹션명, 상태, 부록)
  - 머리말/꼬리말 3개 (섹션 수, 헤더 텍스트, 표지 비활성화)
  - 섹션 번호 2개 (제N장, N.1~N.4)
  - 테이블 디자인 2개 (헤더 배경, 초과 배경)
  - 부록 9개 (A/B/C 포함/제외, 최대건수, 점수, QA)
  - DOCX 카운트 2개 (테이블 수, 섹션 수)
  - PDF 생성 5개 (유효 PDF, 부록 포함/제외 크기, 초과, 빈 섹션)
  - API 통합 5개 (DOCX 옵션, DOCX 전체, PDF 옵션, 미리보기, 404)
- 기존 3개 테스트 ExportContext 호환 수정
- 전체 201개 테스트 통과

### 주요 파일
- `backend/app/services/export_service.py` — DOCX/PDF 전면 개편 (수정)
- `backend/app/api/v1/export.py` — 옵션 파라미터 + 미리보기 API (수정)
- `backend/tests/test_export_format.py` — 40개 신규 테스트 (신규)
- `backend/tests/test_narrative_generator.py` — ExportContext 호환 수정 (수정)
- `src/types/export.ts` — ExportPreview/ExportOptions 타입 (신규)
- `src/lib/qa-api.ts` — 미리보기 API + 옵션 파라미터 지원 (수정)
- `src/components/qa/export-preview.tsx` — 문서 구조 미리보기 패널 (신규)
- `src/components/qa/export-button.tsx` — 옵션 통합 (수정)

### 커밋
- `97c4daa` — feat: Post-5 문서 포맷 고도화 — DOCX/PDF 템플릿 전면 개편

---

## Post-6: LLM adapter 연동 ✅

### 완료 항목

#### LLM adapter 인터페이스 (`backend/app/llm/`)
- `BaseLLMAdapter` 추상 클래스: `enhance_narrative(EnhanceInput) → EnhanceResult`
- 입력: 섹션 키, 제목, 템플릿 서술문, 통계 요약, 기준비교 요약
- 출력: 보강된 서술문, 사용 adapter, fallback 여부

#### None adapter (`backend/app/llm/none_adapter.py`)
- 기본값 (LLM_ADAPTER=none)
- 템플릿 서술문 그대로 반환, LLM 없이 시스템 완전 작동

#### OpenAI adapter (`backend/app/llm/openai_adapter.py`)
- OPENAI_API_KEY 환경변수 사용
- 모델: gpt-4o-mini (비용 효율)
- 환경영향평가서 전문 작성자 시스템 프롬프트
- API 실패 시 템플릿 서술문 그대로 반환 (fallback)

#### Gemini adapter (`backend/app/llm/gemini_adapter.py`)
- GOOGLE_API_KEY 환경변수 사용
- 모델: gemini-2.0-flash (무료 티어)
- 동일 시스템 프롬프트 및 fallback 로직
- httpx 기반 REST API 직접 호출

#### adapter 설정
- 환경변수: LLM_ADAPTER=none|openai_paid|gemini_free (기본값: none)
- factory 함수: `get_llm_adapter()` — 설정에 따라 adapter 반환
- requirements.txt에 `openai>=1.0.0` 추가

#### API 엔드포인트
- GET /api/v1/llm/status — 현재 adapter 설정 및 API 키 상태
- POST /api/v1/llm/projects/{id}/enhance — 섹션 서술문 AI 보강
  - 통계 + 기준비교 데이터 자동 수집 → LLM 보강 → 원본/보강 비교 반환

#### 프론트엔드
- LLM 타입 정의 (`src/types/llm.ts`): LLMStatus, EnhanceResponse
- LLM API 클라이언트 (`src/lib/llm-api.ts`): getLLMStatus, enhanceSectionNarrative
- ScaffoldSectionView: "AI 문체 보강" 버튼 + 보강 전/후 병렬 비교 미리보기
  - 보강 성공 시 좌우 분할 (원본 vs AI 보강)
  - "원본 복원" 버튼으로 되돌리기
  - adapter 이름 뱃지 표시
- LLMStatusCard: 사이드바에 현재 adapter 상태 및 API 키 설정 표시
- draft 페이지에 projectId 전달 및 LLMStatusCard 통합

### 테스트
- `backend/tests/test_llm_adapter.py`: 29개 신규 테스트
  - None adapter 4개 (반환, 이름, 가용성, 빈 템플릿)
  - OpenAI adapter 8개 (이름, 가용성, fallback, 성공, API 오류, 빈 응답, 프롬프트)
  - Gemini adapter 8개 (동일 구조)
  - Factory 함수 5개 (none, openai, gemini, 알 수 없는 값, 대소문자)
  - 기본 인터페이스 3개 (fallback, 입력 데이터, 출력 데이터)
- 전체 230개 테스트 통과

### 주요 파일
- `backend/app/llm/__init__.py` — adapter factory (신규)
- `backend/app/llm/base.py` — BaseLLMAdapter 추상 클래스 (신규)
- `backend/app/llm/none_adapter.py` — None adapter (신규)
- `backend/app/llm/openai_adapter.py` — OpenAI adapter (신규)
- `backend/app/llm/gemini_adapter.py` — Gemini adapter (신규)
- `backend/app/config.py` — LLM_ADAPTER 설정 추가 (수정)
- `backend/app/api/v1/llm.py` — LLM API 엔드포인트 (신규)
- `backend/app/main.py` — LLM 라우터 등록 (수정)
- `backend/requirements.txt` — openai 패키지 추가 (수정)
- `backend/tests/test_llm_adapter.py` — 29개 테스트 (신규)
- `src/types/llm.ts` — LLM TypeScript 타입 (신규)
- `src/lib/llm-api.ts` — LLM API 클라이언트 (신규)
- `src/components/section/scaffold-section-view.tsx` — AI 보강 UI (수정)
- `src/components/section/llm-status-card.tsx` — LLM 상태 카드 (신규)
- `src/app/projects/[id]/draft/page.tsx` — LLM 통합 (수정)

### 커밋
- `a891421` — feat: Post-6 LLM adapter 인터페이스 및 백엔드 구현
- `2bdca7d` — feat: Post-6 프론트엔드 — AI 문체 보강 UI 및 LLM 상태 표시

---

## Post-7: 통합 테스트 및 최종 데모 ✅

### 완료 항목

#### 통합 데모 스크립트 업데이트 (`scripts/demo_full_scenario.py`)
- 기존 7단계 → 11단계로 확장
  1. 프로젝트 생성
  2. 데이터 수집 (4종 커넥터 + 수동 2종)
     - 에어코리아 대기질, 수질, 토양측정망(Post-4), 기상청 ASOS(Post-4)
     - 소음·진동 수동, 생태 수동 + 대기질 연평균 보충
  3. 유사사례 등록 및 매칭
  4. 섹션 플래너 충족도 확인
  5. 통계 엔진 실행 (Post-1)
  6. 환경기준 비교 실행 (Post-2)
  7. 초안 뼈대 + 서술문 생성 확인 (Post-3)
  8. LLM 보강 실행 (Post-6, adapter 상태에 따라)
  9. QA 실행
  10. DOCX + PDF export (부록 A/B/C 포함, Post-5 포맷)
  11. 결과 요약 비교 (MVP vs Post-MVP 기능 비교 표)
- 커넥터 실패 시 수동 fallback 데이터 자동 대체
- 각 단계별 상세 결과 콘솔 출력

#### 전체 테스트 확인
- 230개 전체 테스트 통과 확인
- 테스트 분포:
  - test_connectors.py: 52개 (4종 커넥터)
  - test_export_format.py: 40개 (DOCX/PDF 포맷)
  - test_llm_adapter.py: 29개 (LLM adapter 3종)
  - test_narrative_generator.py: 28개 (서술문 생성기)
  - test_standard_checker.py: 27개 (환경기준 비교)
  - test_spec_alignment.py: 23개 (스펙 정렬)
  - test_statistics.py: 16개 (통계 엔진)
  - test_projects.py: 9개 (프로젝트 CRUD)
  - test_export_pdf.py: 4개 (PDF 출력)
  - test_e2e.py: 1개 (E2E 통합)

#### 문서 최종 업데이트
- `README.md`: Post-1~Post-7 전체 기능 반영
  - 4종 커넥터, 6개 QA 규칙, 3종 LLM adapter, 230개 테스트
  - 통합 데모 실행 방법, 테스트 파일별 건수
- `docs/architecture.md`: 전체 아키텍처 업데이트
  - 시스템 구성도에 4종 커넥터 + LLM adapter 추가
  - 데이터 흐름도에 통계(Post-1), 기준비교(Post-2), 서술문(Post-3), LLM(Post-6) 단계
  - 통계 엔진, 환경기준 비교, 서술문 생성기, LLM adapter, Export 구조 섹션 추가
  - API 엔드포인트 목록에 통계/기준비교/LLM/Export 확장 엔드포인트 추가
- `docs/user-guide.md`: 사용자 가이드 업데이트
  - 전체 사용 흐름 12단계로 확장
  - 4종 커넥터 수집 방법 안내
  - 수동 입력 가이드(Post-4), 통계/기준비교 확인 단계
  - 서술문 유형 설명, AI 문체 보강 사용법
  - DOCX/PDF 문서 구조(표지+목차+4부 구조+부록 3종) 설명
  - LLM 보강 주의사항 추가
- `docs/api-reference.md`: API 레퍼런스 업데이트
  - 통계 API (GET /statistics, /statistics/{key}) 추가
  - 환경기준 비교 API (GET /standards-check, /standards-check/{key}) 추가
  - LLM API (GET /llm/status, POST /llm/projects/{id}/enhance) 추가
  - Export API 확장 (preview, PDF, 부록 옵션)
  - 4종 커넥터 파라미터 상세 추가
- `docs/development.md`: 개발자 가이드 업데이트
  - 서비스 파일 구조 테이블 (8개 서비스 파일)
  - LLM adapter 추가 방법 가이드
  - 테스트 명령어 10종 (파일별 실행)
  - 통합 데모 실행 안내
  - 의존성 목록에 reportlab, openai 추가
- `docs/progress/WORKLOG.md`: Post-7 이력 추가

### 주요 파일
- `scripts/demo_full_scenario.py` — 통합 데모 11단계 (전면 개편)
- `README.md` — 프로젝트 문서 최종 업데이트
- `docs/architecture.md` — 시스템 아키텍처 최종 업데이트
- `docs/user-guide.md` — 사용자 가이드 최종 업데이트
- `docs/api-reference.md` — API 레퍼런스 최종 업데이트
- `docs/development.md` — 개발자 가이드 최종 업데이트
- `docs/progress/WORKLOG.md` — Post-7 이력 추가
- `docs/progress/NEXT_CHAT_BRIEF.md` — 최종 브리핑 업데이트

### 커밋
- `9f969d9` — feat: Post-7 통합 데모 스크립트 11단계 확장
- `902940b` — docs: Post-7 완료 — 문서 최종 업데이트

---

## Post-8: 데이터 파이프라인 정합성 수정 ✅

### 완료 항목

#### 지표명 정합성 수정
- 토양 섹션 `required_indicators`: `중금속_납`→`Pb`, `중금속_카드뮴`→`Cd`, `유류오염_TPH`→`유기물함량`
- 기후 섹션 `required_indicators`: `기온_연평균`→`평균기온`, `강수량_연평균`→`강수량`, `풍향_풍속`→`평균풍속`
- 원인: 커넥터 출력 지표명과 섹션 플래너 필수 지표명이 불일치하여 충족도 0% 표시

#### 토양 환경기준 추가
- `backend/app/data/env_standards.py`에 `SOIL_STANDARDS` 추가
- 토양환경보전법 시행규칙 별표 3 (1지역 우려기준): Cd, Cu, Pb, Zn, Ni, Cr6+ 6개 지표
- `STANDARDS_BY_CATEGORY`에 `"soil": SOIL_STANDARDS` 등록

#### 데모 스크립트 fallback 로직 수정
- 커넥터 `status != "success"` 또는 `evidence_count == 0` 시 수동 fallback 작동
  - 기존: HTTP 응답 자체가 실패해야 fallback. API가 200으로 에러 반환 시 미작동
- 수질 필수 지표 수동 보충 단계(2-b2) 추가
  - 커넥터 API가 과거 데이터(1992~2000) 반환 시 통계 엔진 5년 필터를 통과하는 최신 데이터 보장
- 토양/기후 fallback 지표명을 커넥터 출력과 일치시킴

### 테스트
- 230개 전체 테스트 통과
- 데모 11단계 정상 실행 확인:
  - 수질: BOD/COD/SS/T-N/T-P/DO 통계 + 등급 판정(Ib) + 서술문 생성
  - 토양: Cd/Pb/pH/유기물함량 통계 + 환경기준 비교 + 서술문 생성
  - 기후: 평균기온/강수량/평균풍속 통계 + 서술문 생성
  - DOCX/PDF: 표지+목차+11섹션(6개 데이터 포함)+부록 A/B/C 정상

### 주요 파일
- `backend/app/services/section_planner.py` — 토양/기후 지표명 수정
- `backend/app/data/env_standards.py` — 토양 환경기준 추가
- `backend/tests/test_narrative_generator.py` — 변경된 지표명 반영
- `scripts/demo_full_scenario.py` — fallback 로직 + 수질 보충 + 지표명 정합성

### 커밋
- `14425c0` — fix: 토양/기후 섹션 지표명 정합성 수정 및 토양 환경기준 추가
- `77f3957` — fix: 데모 스크립트 커넥터 fallback 로직 및 수질 보충 데이터 개선

---

## Post-9: 커넥터 2종 추가 + DOCX/LLM 수정 ✅

### 완료 항목

#### Task 1: DOCX/PDF 꼬리말 페이지 번호 수정
- 꼬리말 형식: `- N -` (중앙 정렬)
- OOXML fldChar 구조를 begin/instrText/separate/placeholder/end로 분리
- PDF도 동일 형식 적용

#### Task 2: 토양 3.3 환경기준 비교 누락 수정
- 필터 조건을 `r.status != CheckStatus.NA`에서 `r.standard_value is not None`으로 변경
- DOCX/PDF 모두 적용 — 환경기준이 정의된 모든 지표가 비교 테이블에 포함

#### Task 3: V-world 토지이용 + 국가유산청 문화재 커넥터 추가
- `vworld_land_use`: V-world 2D데이터 API 기반, geomFilter POINT 좌표 → 용도지역구분/지목/용도지구
- `cultural_heritage`: 국가유산청 Open API (XML), 시도코드 추론 + Haversine 반경 1km 필터 → 문화재명/종별/이격거리
- section_planner 필수 지표명: 토지이용(용도지역구분, 용도지구, 지목), 문화재(문화재명, 이격거리)
- 프론트엔드 collect-data-dialog에 경도/위도 파라미터 UI 추가
- 단위 테스트 18건 추가 (전체 69건 통과)
- 데모 스크립트 + 라이브 테스트 스크립트 확장

#### Task 4: LLM 보강 서술문 → DOCX export 반영
- `DraftNarrative` 모델 + Alembic 마이그레이션 추가
- LLM enhance 엔드포인트에서 보강 결과를 DB에 저장 (upsert)
- draft_scaffold가 저장된 LLM 서술문을 우선 사용

#### Task 5: 최종 검증
- 전체 247개 테스트 통과
- 데모 11단계 실행: 6개 커넥터(fallback 포함) + 수동 2종
- 섹션 충족도: 8개 완료(100%) + 3개 미수집
- DOCX 검증: 꼬리말 `- N -`, 토양 3.3 환경기준 비교, 토지이용/문화재 데이터, 11개 섹션
- PDF: 유효 생성 (103.8 KB)

### 커밋
- `e63ce88` — fix: DOCX/PDF 꼬리말 페이지 번호 + 토양 3.3 환경기준 비교
- `0beae0e` — feat: V-world 토지이용 + 국가유산청 문화재 커넥터 2종 추가
- `a3f74f7` — fix: LLM 보강 서술문이 DOCX export에 반영되도록 수정
- `5804894` — fix: 국가유산청 API URL을 https로 수정

---

## Post-10: 전체 문서 최신화 + 프론트엔드 지표명 정합성 ✅

### 완료 항목

#### 전체 문서 Post-9 기준 최신화
- README.md: 커넥터 4종→6종, 테스트 230→247개, 필수 지표명 업데이트, VWORLD_API_KEY 안내
- architecture.md: 시스템 구성도에 V-world/국가유산청 추가, draft_narratives 테이블, 토양 환경기준
- api-reference.md: 커넥터 6종 응답 + V-world/문화재 파라미터 추가
- development.md: 마이그레이션 4건, 테스트 247개, 커넥터 6종 반영
- user-guide.md: 데이터 수집 커넥터 6종 반영

#### 프론트엔드 수동 입력 지표명 정합성
- evidence-form-dialog.tsx: 토지이용 지표명 수정 (용도지역→용도지역구분, 토지피복→용도지구, 개발면적→지목)
- evidence-form-dialog.tsx: 문화재 지표명 수정 (문화재_목록→문화재명)
- 토지이용/문화재 커넥터 자동 수집 가능 안내 힌트 추가

#### 개선 계획 문서 최신화
- post-mvp-improvement-plan.md: Post-1~Post-9 전체 완료 체크, 현황 테이블 갱신, Post-8/9 추가

#### 기타
- `backend/=1.0.0` pip install 아티팩트 삭제

### 커밋
- `defc325` — docs: 전체 문서 Post-9 기준 최신화
- `5a8ec71` — fix: 프론트엔드 수동 입력 지표명 정합성 + 개선 계획 문서 최신화

---

## 전체 커밋 이력 (61건+)

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
| 49 | `66421e6` | docs: Post-4 완료 — 문서 업데이트 |
| 50 | `97c4daa` | feat: Post-5 문서 포맷 고도화 — DOCX/PDF 템플릿 전면 개편 |
| 51 | `d2a9b00` | docs: Post-5 완료 — 문서 업데이트 |
| 52 | `a891421` | feat: Post-6 LLM adapter 인터페이스 및 백엔드 구현 |
| 53 | `2bdca7d` | feat: Post-6 프론트엔드 — AI 문체 보강 UI 및 LLM 상태 표시 |
| 54 | `e63ce88` | fix: DOCX/PDF 꼬리말 페이지 번호 + 토양 3.3 환경기준 비교 |
| 55 | `0beae0e` | feat: V-world 토지이용 + 국가유산청 문화재 커넥터 2종 추가 |
| 56 | `a3f74f7` | fix: LLM 보강 서술문이 DOCX export에 반영되도록 수정 |
| 57 | `5804894` | fix: 국가유산청 API URL을 https로 수정 |
| 58 | `a4077db` | docs: Post-9 완료 — 문서 최종 업데이트 |
| 59 | `defc325` | docs: 전체 문서 Post-9 기준 최신화 |
| 60 | `5a8ec71` | fix: 프론트엔드 수동 입력 지표명 정합성 + 개선 계획 문서 최신화 |
| 61 | `41760d1` | docs: Post-10 완료 — 문서 최신화 작업 기록 |
| 62 | `5603382` | fix: 비수치형 서술문 불일치 + 부록 B 유사사례 중복 수정 (Post-11) |
| 63 | `0bff1c7` | feat: 법령 데이터 구축 (Reg-1) |
| 64 | `359420c` | feat: 서술문 법적 근거 반영 (Reg-2) |
| 65 | `2e6b8c1` | feat: QA 규칙 정밀화 — R007/R008 법적 필수 항목 검증 (Reg-3) |
| 66 | `1c06bbc` | feat: 사업유형별 평가 범위 자동 판단 (Reg-4) |
| 67 | `016f08a` | docs: Reg-4 완료 — 문서 최신화 작업 기록 |
| 68 | `25d66d1` | docs: Reg-5 통합 검증 + 문서화 — 법령 반영 Phase 완료 |
| 69 | `681da2b` | fix: 서술문 법적 근거 누락 방지 + 유사사례 중복 제거 |

---

## Bugfix: 서술문 법적 근거 누락 + 유사사례 중복 재발

### 문제 1: 서술문/테이블에 법적 근거 미반영
- 원인: LLM 보강 서술문이 법적 근거 없이 저장되면 템플릿 서술문 대신 사용됨
- 수정: draft_scaffold.py — LLM 보강 서술문에 법적 근거 키워드 없으면 템플릿 서술문으로 대체

### 문제 2: 부록 B 유사사례 중복 재발
- 원인: similarity.py에서 이름 기준 중복 제거가 top_k 슬라이싱 이후에 실행됨
- 수정: similarity.py — 이름 기준 중복 제거를 top_k 슬라이싱 전으로 이동

### 테스트
- 5개 신규 테스트 추가 (370개 전체 통과)

### 검증 결과
- 대기질/수질/토양/소음 서술문에 법적 근거 포함 확인
- 환경기준 비교 테이블 4개에 "법적 근거" 열 + 값 확인
- 부록 B 유사사례 3건 고유 확인

### 커밋
- `681da2b` — fix: 서술문 법적 근거 누락 방지 + 유사사례 중복 제거

---

## Post-11: 비수치형 서술문 + 유사사례 중복 수정

### 완료 항목
- 이슈 1: 토지이용/문화재 등 비수치형 데이터가 있는 섹션에서 "수집되지 않았다" 서술문이 출력되는 문제 수정
  - `statistics.py`: `TextIndicatorInfo` 데이터클래스 추가, `SectionStats`에 `total_text_count`/`text_indicators` 필드 추가
  - `statistics.py`: `_fetch_text_evidences()` 함수 추가, `calculate_section_statistics()`에서 비수치형 데이터도 집계
  - `narrative_generator.py`: `generate_land_use_narrative()` — 토지이용 전용 서술문 (지목, 용도지역, 용도지구)
  - `narrative_generator.py`: `generate_cultural_heritage_narrative()` — 문화재 전용 서술문 (문화재명+이격거리)
  - `narrative_generator.py`: `_has_any_data()` / `_text_indicator_map()` 공통 헬퍼 추가
  - `narrative_generator.py`: `generate_generic_narrative()` / `generate_narrative()` — 비수치형 데이터도 인식
- 이슈 2: 부록 B 유사사례 중복 표시 문제 수정
  - `export_service.py`: 유사사례 목록 생성 시 이름 기준 중복 제거 (점수 높은 것 우선)
  - `export_service.py`: preview 유사사례 수 산출에도 중복 제거 적용
- 테스트 9개 추가 (256개 전체 통과)
  - 토지이용 서술문 4개, 문화재 서술문 4개, 범용 비수치 1개

### 커밋
- `5603382` — fix: 비수치형 서술문 불일치 + 부록 B 유사사례 중복 수정 (Post-11)

---

## Reg-1: 법령 데이터 구축 ✅

### 완료 항목

#### 1. 법령 데이터 폴더 생성
- `backend/app/data/regulations/` 폴더 및 `__init__.py` 생성

#### 2. legal_references.py — 환경기준별 법적 근거 매핑
- `LegalReference` 데이터클래스: 법률명, 조문, 법적 근거 문자열, 설명
- `IndicatorLegalInfo` 데이터클래스: 지표명, 기준값, 단위, 법적 근거
- 매체별 법적 근거 상수: `AIR_LEGAL_REF`, `WATER_LEGAL_REF`, `NOISE_LEGAL_REF`, `SOIL_LEGAL_REF`
- 카테고리→법적 근거 매핑: `CATEGORY_LEGAL_REFS`
- 지표별 법적 근거 매핑: `AIR_INDICATOR_REFS`, `WATER_INDICATOR_REFS`, `NOISE_INDICATOR_REFS`, `SOIL_INDICATOR_REFS`
- 통합 매핑: `ALL_INDICATOR_REFS` (전체 지표 → 법적 근거)
- 조회 함수: `get_legal_reference()`, `get_category_legal_reference()`

#### 3. required_items.py — 사업유형별 필수 평가 항목
- `RequiredSection`, `ProjectTypeRequirement` 데이터클래스
- 12개 사업유형 정의: power_plant, road, housing, industrial, tourism, port, military, railway, airport, dam, reclamation, other
- 각 유형별 필수 섹션 + 섹션별 필수 지표 목록
- military는 전 항목(11개 섹션) 필수
- 미등록 유형은 'other' 기준 적용
- 조회 함수: `get_required_sections()`, `get_required_indicators()`, `get_project_type_requirement()`

#### 4. area_classifications.py — 지역구분별 기준 차등
- `NoiseStandardByArea` 데이터클래스
- 소음환경기준 4개 지역구분 ("가", "나", "다", "라")
- 일반지역/도로변지역 × 주간/야간 = 4개 기준값씩
- 간편 조회용 딕셔너리: `NOISE_AREA_GENERAL`, `NOISE_AREA_ROADSIDE`
- 조회 함수: `get_noise_standard()`, `get_noise_area_info()`

#### 5. env_standards.py 확장
- `Standard` 데이터클래스에 `legal_basis: str = ""` 필드 추가 (하위 호환)
- 대기 16개, 수질 6개, 소음 2개, 토양 6개 기준 모두 법적 근거 값 설정
- 기존 로직(`get_standard_for_indicator`, `get_standards_for_category`, `determine_water_grade` 등) 동작 유지

### 테스트
- `backend/tests/test_regulations.py`: 53개 신규 테스트
  - TestLegalReferences (12개): 법적 근거 매핑 무결성 — 모든 기준에 법적 근거 매핑, 필드 채움, 기준값 일치
  - TestRequiredItems (20개): 사업유형별 필수 항목 완전성 — 12개 유형 정의, 섹션/지표 비어있지 않음, 개별 유형 검증
  - TestAreaClassifications (17개): 지역구분 구조 — 4개 지역, 주간/야간 값, 도로변>일반, 주간>야간
  - TestEnvStandardsCompat (6개): 하위 호환성 — legal_basis 속성, 기존 필드 유지, 기존 함수 정상 동작
- 기존 256개 + 신규 53개 = 309개 전체 통과

### 주요 파일
- `backend/app/data/regulations/__init__.py` — 패키지 초기화 (신규)
- `backend/app/data/regulations/legal_references.py` — 법적 근거 매핑 (신규)
- `backend/app/data/regulations/required_items.py` — 사업유형별 필수 항목 (신규)
- `backend/app/data/regulations/area_classifications.py` — 지역구분별 기준 차등 (신규)
- `backend/app/data/env_standards.py` — legal_basis 필드 추가 (수정)
- `backend/tests/test_regulations.py` — 법령 데이터 테스트 53개 (신규)

---

## Reg-2: 서술문 법적 근거 반영 ✅

### 완료 항목

#### 1. standard_checker.py — IndicatorCheckResult에 legal_basis 필드 추가
- `IndicatorCheckResult` 데이터클래스에 `legal_basis: str = ""` 필드 추가
- `_check_indicator()`: `Standard.legal_basis`를 결과에 복사
- 기준은 있지만 측정 데이터 없는 지표에도 `legal_basis` 설정
- `_format_legal_ref()` 헬퍼: 법적 근거 문자열을 서술문 삽입 형태로 변환
- `_generate_section_summary()`: 지표별 판정 서술에 법적 근거 접두어 삽입

#### 2. narrative_generator.py — 서술문에 법적 근거 자동 삽입
- 섹션별 법적 근거 접두어 상수 정의:
  - `_AIR_LEGAL_PREFIX`: "환경정책기본법 시행령 별표 제1호에 따른 대기환경기준"
  - `_WATER_LEGAL_PREFIX`: "환경정책기본법 시행령 별표 제1호에 따른 하천 수질 및 수생태계 생활환경기준"
  - `_NOISE_LEGAL_PREFIX`: "환경정책기본법 시행령 별표 제1호에 따른 소음환경기준"
- `_LEGAL_REF_NARRATIVE` 매핑: 법적 근거 원문 → 서술문용 텍스트
- 대기질: "환경기준(50 ug/m3)" → "대기환경기준(연평균 50 ug/m3)" + 법적 근거
- 수질: "하천 생활환경기준 Ib등급(좋음)" → "하천 수질 및 수생태계 생활환경기준 Ib등급(좋음, BOD 2 mg/L 이하)" + 법적 근거
- 소음: "환경기준(55 dB(A))" → '소음환경기준(일반지역 "나" 주간 55 dB(A))' + 법적 근거
- 범용(토양): 법적 근거가 있으면 "토양오염우려기준(1지역 4 mg/kg) 이내" 형태로 서술
- `_get_water_grade_bod()`: 수질등급 BOD 상한값 조회 헬퍼
- `_extract_area_from_description()`: 기준 설명에서 지역구분 추출 헬퍼

#### 3. draft_scaffold.py — 환경기준 비교 테이블에 "법적 근거" 열 추가
- `_format_stats_summary()`: 테이블 헤더에 "법적 근거" 열 추가
- `_short_legal_ref()` 헬퍼: 간략 형태 변환 ("환경정책기본법 별표1", "토양환경보전법 별표3")
- 각 데이터 행에 간략 법적 근거 표시

#### 4. export_service.py — DOCX/PDF 환경기준 비교 테이블 법적 근거 열 반영
- `_docx_add_standards_table()`: 5열→6열 (+ "법적 근거"), 열 너비 재조정
- `_pdf_add_standards_table()`: 5열→6열 (+ "법적 근거"), 열 너비 재조정
- `_short_legal_ref()` 헬퍼 추가

#### 5. 프론트엔드
- scaffold-section-view.tsx의 `summary_text`가 `<pre>` 태그로 렌더링되어 법적 근거 열 자동 표시
- 서술문의 법적 근거 텍스트도 narrative 필드에 포함되어 그대로 출력

### 테스트
- 14개 신규 테스트 (기존 309 + 신규 14 = 323개 전체 통과)
  - TestLegalBasisInNarrative (8개): 대기/수질/소음/토양 서술문 법적 근거 포함 검증
  - TestLegalBasisInScaffold (2개): scaffold 테이블 법적 근거 열 포함/미포함 검증
  - TestLegalBasisInStandardChecker (4개): IndicatorCheckResult 필드, _format_legal_ref 변환 검증

### 주요 파일
- `backend/app/services/standard_checker.py` — legal_basis 필드 추가, 법적 근거 변환 (수정)
- `backend/app/services/narrative_generator.py` — 서술문 법적 근거 삽입 (수정)
- `backend/app/services/draft_scaffold.py` — scaffold 테이블 법적 근거 열 (수정)
- `backend/app/services/export_service.py` — DOCX/PDF 테이블 법적 근거 열 (수정)
- `backend/tests/test_narrative_generator.py` — 14개 신규 테스트 (수정)

---

## Reg-3: QA 규칙 정밀화 ✅

### 완료 항목

#### 1. qa_engine.py — R007/R008 법적 필수 항목 검증 + R001 동적 판단
- `QaIssue` 데이터클래스에 `legal_basis: str = ""` 필드 추가
- `_CRITICAL_SECTIONS` 하드코딩 → `_get_critical_sections(project_type)` 동적 함수로 교체
  - 사업유형 설정 시: `required_items.get_required_sections()` 사용
  - 미설정 시: 기존 4개 핵심 섹션 fallback 유지
- `_get_project_type_name()` 헬퍼: 사업유형 코드 → 한글명 변환
- R001 수정: `critical_sections` 매개변수 + `legally_required` 플래그
  - 법적 필수 섹션은 R007에서 처리하므로 R001에서 건너뜀
- R002 수정: `critical_sections` 매개변수 사용 (동적 심각도)
- R007 신규: 법적 필수 섹션 누락 (critical, legal_basis 포함)
  - 메시지: "{사업유형} 사업은 환경영향평가법 시행령 별표 3에 따라 {섹션명} 평가가 필수입니다."
- R008 신규: 법적 필수 지표 누락 (warning, legal_basis 포함)
  - required_items의 섹션별 법적 필수 지표 기준으로 누락 검출
- `run_qa()`: DB에서 project_type 조회 후 동적 규칙 적용

#### 2. QA 결과 스키마 수정
- `backend/app/schemas/qa.py`: `QaIssueRead`에 `legal_basis` 필드 추가
- `backend/app/api/v1/qa.py`: 변환 시 `legal_basis` 전달

#### 3. QA 결과 UI 수정
- `src/types/qa.ts`: `QaIssue` 인터페이스에 `legal_basis` 필드 추가
- `src/components/qa/qa-issue-list.tsx`:
  - `legal_basis`가 있는 critical 이슈: 빨간 배경(`bg-red-50`) + 빨간 테두리(`border-red-300`)
  - 법적 근거 텍스트 표시: "근거: {legal_basis}" (빨간색, 작은 글씨)

#### 4. Export 수정
- DOCX 부록 C: 6열→7열 (+ "법적 근거"), 열 너비 재조정
- PDF 부록 C: 5열→6열 (+ "법적 근거"), 열 너비 재조정

#### 5. 기존 테스트 호환성 수정
- `test_e2e.py`: industrial 사업유형 → ecology R001 severity "critical"→"warning" (올바른 변경)
  - industrial 필수 섹션 보충 데이터 추가 (soil, waste)
- `test_export_format.py`: power_plant 필수 섹션 토지이용 증거 추가
- `test_export_pdf.py`: power_plant 필수 섹션 토지이용 증거 추가

### 테스트
- 22개 신규 테스트 (기존 323 + 신규 22 = 345개 전체 통과)
  - TestR007RequiredSectionMissing (7개): 사업유형별 R007 동작 검증
  - TestR008RequiredIndicatorMissing (5개): R008 동작 검증
  - TestR001DynamicCritical (5개): 동적 심각도 판단 검증
  - TestQaIssueLegalBasis (4개): legal_basis 필드 및 사업유형명 변환
  - TestQaExportLegalBasisColumn (1개): DOCX 부록 C 법적 근거 열 검증

### 주요 파일
- `backend/app/services/qa_engine.py` — R007/R008 추가, R001/R002 동적 판단 (수정)
- `backend/app/schemas/qa.py` — legal_basis 필드 (수정)
- `backend/app/api/v1/qa.py` — legal_basis 전달 (수정)
- `backend/app/services/export_service.py` — 부록 C 법적 근거 열 (수정)
- `src/types/qa.ts` — QaIssue 타입 (수정)
- `src/components/qa/qa-issue-list.tsx` — 법적 근거 표시 + R007 스타일 (수정)
- `backend/tests/test_regulations.py` — 22개 신규 테스트 (수정)
- `backend/tests/test_e2e.py` — 기존 테스트 호환성 수정
- `backend/tests/test_export_format.py` — 기존 테스트 호환성 수정
- `backend/tests/test_export_pdf.py` — 기존 테스트 호환성 수정

---

## Reg-4: 사업유형별 평가 범위 자동 판단 ✅

### 완료 항목

#### 1. 평가 범위 서비스 (scope_service.py) — 신규
- `get_assessment_scope(project_type)`: 사업유형별 필수/권장/선택 섹션 분류
- 12개 사업유형 지원, 미등록 유형은 'other' 기준 적용
- 필수 섹션의 법적 필수 지표 목록 포함
- `SectionScope`, `AssessmentScope` 데이터 구조 정의

#### 2. API: GET /api/v1/projects/{id}/assessment-scope — 신규
- `backend/app/api/v1/scope.py`: 라우터 + 엔드포인트
- `backend/app/schemas/scope.py`: AssessmentScopeRead, SectionScopeRead 스키마
- `backend/app/main.py`: scope_router 등록

#### 3. 섹션 플래너 연동 (section_planner.py)
- `calculate_section_status()`: project_type 파라미터 추가
- 필수 섹션 empty → `expert_required` 상태 전환
- 선택 섹션 empty → `not_applicable` 상태 전환
- `SectionStatus`에 `scope` 필드 추가 ("required"/"optional"/"")
- `calculate_all_sections_status()`: project_type 전달
- API(sections.py): 프로젝트에서 project_type 조회 후 전달

#### 4. 프론트엔드
- `src/types/section.ts`: SectionScopeValue, AssessmentScope, SECTION_SCOPE_LABELS 추가
- `src/types/project.ts`: tourism, military 유형 추가 + PROJECT_TYPE_LABELS 매핑
- `src/lib/section-api.ts`: getAssessmentScope() 함수 추가
- `src/components/section/section-status-card.tsx`: 필수/권장/선택 배지 + 필수 미충족 빨간 테두리
- `src/app/projects/[id]/sections/page.tsx`: 평가 범위 요약 바 (필수 N/M, 권장, 선택)
- `src/app/projects/[id]/evidences/page.tsx`: 필수 섹션 미수집 지표 경고 패널
- `src/app/projects/page.tsx`: 사업유형 한글 라벨 표시
- `backend/app/schemas/section.py`: SectionStatusRead에 scope 필드 추가

#### 5. DOCX/PDF 목차 개선
- DOCX 목차: '구분' 열 추가 (필수/선택), 필수 미수집 빨간 배경
- PDF 목차: '구분' 열 추가 (필수/선택), 필수 미수집 빨간 텍스트
- DOCX/PDF 섹션 본문: "본 사업({유형})에서 {섹션} 항목은 환경영향평가법 시행령에 따라 필수 평가 항목에 해당한다." 안내 문구 삽입
- ExportContext에 required_section_keys 필드 추가

#### 6. 기존 테스트 호환성 수정
- `test_e2e.py`: ecology 상태 "empty"→"not_applicable" (industrial에서 선택 섹션)
  - soil scope="required" + status="expert_required" 검증 추가

### 테스트
- 20개 신규 테스트 (기존 345 + 신규 20 = 365개 전체 통과)
  - TestScopeService (10개): 12개 사업유형 범위 반환 검증
  - TestSectionPlannerScopeIntegration (4개): 상태 연동 검증
  - TestScopeAPI (3개): API 엔드포인트 검증
  - TestExportScopeTOC (3개): 목차 구분열/안내문구 검증

### 주요 파일
- `backend/app/services/scope_service.py` — 평가 범위 서비스 (신규)
- `backend/app/api/v1/scope.py` — 평가 범위 API (신규)
- `backend/app/schemas/scope.py` — 평가 범위 스키마 (신규)
- `backend/app/services/section_planner.py` — scope 연동 (수정)
- `backend/app/services/export_service.py` — 목차 구분열 + 필수 안내문구 (수정)
- `backend/app/api/v1/sections.py` — project_type 전달 (수정)
- `backend/app/schemas/section.py` — scope 필드 (수정)
- `backend/app/main.py` — scope_router 등록 (수정)
- `src/types/section.ts` — SectionScopeValue 등 타입 (수정)
- `src/types/project.ts` — PROJECT_TYPE_LABELS (수정)
- `src/components/section/section-status-card.tsx` — 범위 배지 (수정)
- `src/app/projects/[id]/sections/page.tsx` — 범위 요약 바 (수정)
- `src/app/projects/[id]/evidences/page.tsx` — 미수집 지표 경고 (수정)

---

## Reg-5: 통합 검증 + 문서화 ✅

### 완료 항목

#### 1. 데모 스크립트 업데이트 (scripts/demo_full_scenario.py)
- 기존 11단계에 "단계 4.5: 법령 반영 검증" 추가
  - a. 평가 범위 API 조회 (power_plant → 필수 5, 권장 2, 선택 4)
  - b. 섹션 상태 scope 필드 확인 (required/recommended/optional)
  - c. 서술문 법적 근거 포함 여부 검증 (환경정책기본법, 토양환경보전법 등)
  - d. 환경기준 비교 지표별 legal_basis 존재 확인
  - e. 검증 결과 4항목 합격/불합격 요약 출력
- QA 실행(단계 9)에서 R007/R008 이슈 건수 및 법적 근거 표시 추가
- 최종 요약(단계 11)에 법령 반영 현황 섹션 추가
- 기능 비교 표에 "법령 반영 (Reg)" 열 추가 (8개 QA 규칙, 12개 사업유형, 법적 근거 등)
- 스크립트 헤더 "Post-9 최종판" → "Reg-5 최종판" 업데이트

#### 2. 전체 테스트 실행
- 365개 전체 테스트 통과 (변경 없음)
- 테스트 분포:
  - test_regulations.py: 95개 (법령 데이터 + QA 규칙 + 평가 범위)
  - test_connectors.py: 69개 (6종 커넥터)
  - test_narrative_generator.py: 51개 (서술문 생성기 + 법적 근거)
  - test_export_format.py: 40+개 (DOCX/PDF 포맷)
  - test_llm_adapter.py: 29개 (LLM adapter)
  - test_standard_checker.py: 27개 (환경기준 비교)
  - test_spec_alignment.py: 23개 (스펙 정렬)
  - test_statistics.py: 16개 (통계 엔진)
  - test_projects.py: 9개 (프로젝트 CRUD)
  - test_export_pdf.py: 4개 (PDF 출력)
  - test_e2e.py: 1개 (E2E 통합)

#### 3. 문서 최종 업데이트
- **README.md**: 법령 반영 기능 섹션 추가 (법적 근거 인용, 평가 범위, R007/R008, 법령 데이터 모듈), QA 8개 규칙, 테스트 365개
- **docs/architecture.md**: 법령 데이터 구조도, 평가 범위 서비스 구조, 법적 근거 반영 흐름, QA 8개 규칙 업데이트, API 평가 범위 엔드포인트
- **docs/user-guide.md**: 사업유형별 평가 범위 설명, 섹션 플래너 범위 배지, 서술문 법적 근거 표시, QA 8개 규칙 + R007/R008 설명, Export 목차 필수 표시
- **docs/api-reference.md**: GET /assessment-scope 엔드포인트 추가, QA 응답에 legal_basis 필드, 환경기준 비교 응답에 legal_basis 필드
- **docs/development.md**: 서비스 파일 목록 업데이트 (9개 서비스), 법령 데이터 수정/추가 방법 가이드, QA 규칙 8개, 테스트 365개
- **docs/progress/WORKLOG.md**: Reg-5 이력 추가

### 주요 파일
- `scripts/demo_full_scenario.py` — 법령 반영 검증 단계 추가 (수정)
- `README.md` — 법령 반영 기능 문서화 (수정)
- `docs/architecture.md` — 법령 데이터 구조 + scope_service (수정)
- `docs/user-guide.md` — 평가 범위 + 법적 근거 표시 (수정)
- `docs/api-reference.md` — assessment-scope API + legal_basis 필드 (수정)
- `docs/development.md` — 법령 데이터 수정 가이드 (수정)
- `docs/progress/WORKLOG.md` — Reg-5 이력 (수정)
- `docs/progress/NEXT_CHAT_BRIEF.md` — 최종 브리핑 (수정)

---

## Pred-2: 소음 전파 + 수질 혼합 모델 ✅

### 완료 항목

#### 1. 소음 전파 모델
- `backend/app/services/prediction/noise_propagation.py`
- 점음원 거리감쇠: L(r) = Lw - 20·log10(r) - 11
- 선음원(도로) 감쇠: L(r) = Lw/m - 10·log10(r) - 8
- 보정 요소: 지면 반사(+3dB), 대기 흡수(-α·r), Maekawa 차음벽 회절
- 에너지 합산: L_total = 10·log10(10^(L1/10) + 10^(L2/10))
- 예측 거리: 10m, 20m, 50m, 100m, 200m, 500m (주간/야간 각각)
- 환경기준 비교: 주간 55dB(A), 야간 45dB(A)
- 사업유형별 기본값: power_plant=95dB, road=75dB/m(선음원), housing=90dB, industrial=100dB

#### 2. 수질 혼합 모델
- `backend/app/services/prediction/water_mixing.py`
- 완전혼합 희석: C_mix = (Q_river·C_river + Q_discharge·C_discharge) / (Q_river + Q_discharge)
- 대상 물질: BOD, COD, SS, T-N, T-P
- 방류수 수질기준 적용: BOD 30, COD 40, SS 30, T-N 60, T-P 8 (mg/L, 물환경보전법)
- 하천 환경기준(III등급) 비교: BOD 5, COD 7, SS 25, T-P 0.2 (mg/L)
- 사업유형별 기본 방류량: power_plant=0.01, industrial=0.1, housing=0.05 (m³/s)

#### 3. 레지스트리 및 API 확장
- `prediction/registry.py` — noise_propagation, water_mixing 모델 등록
- 섹션 매핑: noise_vibration → noise_propagation, water_quality → water_mixing
- API 배경 데이터 자동 추출: 소음(주간/야간 Leq), 수질(BOD, COD, SS, T-N, T-P)
- 기존 API 엔드포인트 재사용: POST /predict/{section_key}, GET /prediction-models

#### 4. 테스트 (82개)
- TestPointSourceAttenuation: 점음원 감쇠 (9개, 수동 계산 검증 포함)
- TestLineSourceAttenuation: 선음원 감쇠 (4개)
- TestBarrierAttenuation: Maekawa 차음벽 (7개)
- TestEnergySum: 에너지 합산 (6개, +3dB 법칙 등)
- TestNoisePropagationModel: 모델 통합 (12개)
- TestCompleteMixing: 혼합 계산 (8개)
- TestWaterMixingModel: 모델 통합 (14개)
- TestNoiseDefaults / TestWaterDefaults: 기본값 (10개)
- TestRegistryExtended: 레지스트리 확장 (7개)
- TestPredictionAPIExtended: API (5개)

### 전체 테스트
- 526개 전체 통과 (기존 444 + 신규 82)

### 주요 파일
- `backend/app/services/prediction/noise_propagation.py` (신규)
- `backend/app/services/prediction/water_mixing.py` (신규)
- `backend/app/services/prediction/registry.py` (수정 — 2개 모델 추가)
- `backend/app/services/prediction/__init__.py` (수정)
- `backend/app/api/v1/predictions.py` (수정 — 소음/수질 배경 데이터 함수)
- `backend/tests/test_prediction.py` (수정 — ecology 섹션으로 변경)

---

## Pred-3: 예측 결과 통합 ✅

### 완료 항목

#### 1. Scaffold 서비스 확장 (draft_scaffold.py)
- `ScaffoldSection`에 `prediction_result: PredictionResult | None` 필드 추가
- `ScaffoldSection`에 `prediction_narrative: str` 필드 추가
- `generate_section_scaffold()`에 `project_type` 파라미터 추가
- `_extract_background_data()` 헬퍼 신규: evidence entries에서 배경 농도 자동 추출
  - 대기질: PM10_연평균→PM10, PM2.5_연평균→PM2.5, NO2_연평균→NO2, SO2_연평균→SO2
  - 소음: 소음_Leq_주간, 소음_Leq_야간
  - 수질: BOD, COD, SS, T-N, T-P
- 예측 가능 섹션(air_quality, noise_vibration, water_quality)에서 자동 예측 실행
- `generate_draft_scaffold()`에서 Project 조회하여 project_type 전달

#### 2. 서술문 생성 확장 (narrative_generator.py)
- `generate_prediction_narrative(section_key, prediction_result)` 함수 신규
- 대기질: "가우시안 플룸 모델을 적용하여... 기여농도... 합산... 환경기준 이내/초과"
- 소음: "점음원/선음원 거리감쇠 모델을 적용하여... 예측 소음도... 에너지 합산... 판정"
- 수질: "완전혼합 희석 모델을 적용하여... BOD, COD... 하천 생활환경기준 수준"
- 미지원 섹션: "본 분야에 대한 영향 예측은 별도 전문 분석이 필요하다."

#### 3. DOCX/PDF Export 수정 (export_service.py)
- 섹션 구조 변경: N.1 현황 → N.2 통계 → N.3 기준비교 → **N.4 영향 예측** → N.5 측정데이터
- `_docx_add_prediction_table()` 신규: 예측 결과 테이블 (지점|기여|현황|합산|기준|판정)
- `_pdf_add_prediction_table()` 신규: PDF 동일 구조
- 전제 조건 및 모델 한계 "※" 문단 포함
- 초과 행 빨간 배경 처리
- prediction_result 없는 섹션은 N.4 건너뛰고 기존 구조 유지

#### 4. API 스키마 확장 (schemas/section.py, api/v1/sections.py)
- `ScaffoldSectionRead`에 `prediction_result: PredictionResultRead | None`, `prediction_narrative: str` 추가
- scaffold 엔드포인트에서 prediction_result 변환 로직 추가

#### 5. 프론트엔드 (predictions 페이지)
- `src/types/prediction.ts` 신규: PredictionItem, PredictionResult, ModelInfo, InputParameter 타입
- `src/lib/prediction-api.ts` 신규: getPredictionModels(), runPrediction() API 클라이언트
- `src/app/projects/[id]/predictions/page.tsx` 신규:
  - 섹션별 카드: 모델 선택, 파라미터 입력 폼, 기본값 자동 채움
  - "배경 데이터 사용" 토글 (Switch)
  - 예측 실행 버튼 → 결과 테이블 + 판정 Badge
  - 전제 조건/모델 한계 접이식 영역
- `src/app/projects/[id]/draft/page.tsx` 수정: "영향 예측" 링크 버튼 추가

#### 6. 테스트 (53개 신규)
- `test_prediction_narrative.py` (26개): 서술문 키워드, 초과 판정, 미지원 섹션
- `test_pred3_integration.py` (27개): scaffold 통합, DOCX 구조 검증

### 전체 테스트
- 579개 전체 통과 (기존 526 + 신규 53)

### 주요 파일
- `backend/app/services/draft_scaffold.py` (수정)
- `backend/app/services/narrative_generator.py` (수정)
- `backend/app/services/export_service.py` (수정)
- `backend/app/schemas/section.py` (수정)
- `backend/app/api/v1/sections.py` (수정)
- `backend/tests/test_prediction_narrative.py` (신규)
- `backend/tests/test_pred3_integration.py` (신규)
- `src/types/prediction.ts` (신규)
- `src/lib/prediction-api.ts` (신규)
- `src/app/projects/[id]/predictions/page.tsx` (신규)
- `src/app/projects/[id]/draft/page.tsx` (수정)
- `backend/tests/test_prediction_noise_water.py` (신규 — 82개 테스트)

---

## Pred-1: 예측 모듈 기반 구조 + 대기 확산 모델 ✅

### 완료 항목

#### 1. 예측 엔진 기반 구조
- `backend/app/services/prediction/__init__.py` — 패키지 초기화 및 공개 API
- `backend/app/services/prediction/base.py` — BasePredictionModel 추상 클래스
  - `predict(parameters, background_data)` → PredictionResult
  - `get_required_inputs()` → InputParameter 목록
  - `get_model_info()` → ModelInfo (모델명, 설명, 적용 섹션)
- `backend/app/services/prediction/registry.py` — 모델 레지스트리 (section_key → model 매핑)
- PredictionResult 스키마: section_key, model_name, input_parameters, predictions, summary, assumptions, limitations

#### 2. 대기 확산 모델 (가우시안 플룸)
- `backend/app/services/prediction/air_dispersion.py`
- Pasquill-Gifford 확산계수 (A~F 등급별 σy, σz 경험식)
- 가우시안 플룸 지표면 중심선 농도 공식: C = Q/(π·σy·σz·u) × exp(-H²/(2σz²))
- PM10, PM2.5, NO2, SO2 예측 (ug/m3 통일)
- 풍하거리 6지점: 100m, 200m, 500m, 1km, 2km, 5km
- 배경 농도(에어코리아 현황 데이터) 합산 → 사업 후 예상 농도
- 환경기준 초과 여부 판정
- 사업유형별 기본 배출량 + 굴뚝 높이 딕셔너리

#### 3. API 엔드포인트
- `POST /api/v1/projects/{id}/predict/{section_key}` — 예측 실행
- `GET /api/v1/prediction-models` — 사용 가능한 모델 목록 + 입력 파라미터
- `backend/app/schemas/prediction.py` — Pydantic 응답 스키마
- `backend/app/api/v1/predictions.py` — 라우터 (main.py 등록 완료)
- 배경 농도: 프로젝트 evidence에서 연평균 대기 데이터 자동 추출
- 풍속: 프로젝트 기후 데이터에서 자동 추출 (없으면 기본값 3.0 m/s)

#### 4. 기본값 체계
- power_plant: PM10=0.5, PM2.5=0.3, NO2=1.0, SO2=0.5 (g/s) / 굴뚝 50m
- industrial: PM10=1.0, PM2.5=0.5, NO2=2.0, SO2=1.0 (g/s) / 굴뚝 30m
- 기타 유형: power_plant의 50% / 굴뚝 20m
- 대기안정도: 기본 D(중립), A~F 선택 가능

#### 5. 테스트 (74개)
- TestSigmaCoefficients: 확산계수 계산 (12개, 안정도 등급별 파라메트릭 포함)
- TestGaussianPlume: 가우시안 플룸 농도 계산 (12개, 수동 계산 검증 포함)
- TestAirDispersionModel: 모델 클래스 통합 (14개)
- TestDefaults: 사업유형별 기본값 (6개)
- TestRegistry: 모델 레지스트리 (7개)
- TestPredictionAPI: API 엔드포인트 (4개)
- TestBasePredictionModel: 추상 클래스 검증 (3개)

### 전체 테스트
- 444개 전체 통과 (기존 370 + 신규 74)

### 주요 파일
- `backend/app/services/prediction/__init__.py` (신규)
- `backend/app/services/prediction/base.py` (신규)
- `backend/app/services/prediction/air_dispersion.py` (신규)
- `backend/app/services/prediction/registry.py` (신규)
- `backend/app/schemas/prediction.py` (신규)
- `backend/app/api/v1/predictions.py` (신규)
- `backend/app/main.py` (수정 — predictions_router 등록)
- `backend/tests/test_prediction.py` (신규 — 74개 테스트)

---

## Pred-3: 예측 결과 통합 ✅

### 완료 항목

#### 1. draft_scaffold.py 확장
- `ScaffoldSection` 데이터클래스에 `prediction_result: PredictionResult | None`, `prediction_narrative: str` 필드 추가
- `_extract_background_data()` 헬퍼 함수 신규: evidence 항목에서 섹션별 배경 농도 추출
  - 대기질: PM10_연평균 → PM10, PM2.5_연평균 → PM2.5, NO2_연평균 → NO2, SO2_연평균 → SO2
  - 소음: 소음_Leq_주간/야간 그대로 매핑
  - 수질: BOD, COD, SS, T-N, T-P 그대로 매핑
- `generate_section_scaffold()`: `project_type` 파라미터 추가 + 예측 모델 자동 실행
- `generate_draft_scaffold()`: Project 테이블 조회로 `project_type` 취득 후 전달

#### 2. narrative_generator.py 확장
- `generate_prediction_narrative(section_key, prediction_result) → str` 함수 신규
- 대기질: 가우시안 플룸 기반 오염물질별 100m 지점 기여농도 + 현황 + 합산 + 법적 근거 + 판정
- 소음: 점음원 거리감쇠 기반 주간/야간 최근접 수음점 소음도 + 에너지 합산 + 판정
- 수질: 완전혼합 희석 기반 BOD, COD 혼합 후 농도 + 기타 항목 + 초과 시 처리 대책
- 미지원 섹션: "본 분야에 대한 영향 예측은 별도 전문 분석이 필요하다." 반환

#### 3. export_service.py 확장 (DOCX + PDF)
- `_docx_add_section()`: prediction_result가 있는 섹션에 N.4 영향 예측 소챕터 삽입
  - N.4: 적용 모델 / 예측 서술문 / 예측 결과 테이블 / 전제 조건 / 모델 한계
  - N.5(기존 N.4): 측정 데이터 (측정번호 자동 조정)
- `_docx_add_prediction_table()` 함수 신규
  - 수질: 항목 | 방류수 | 하천현황 | 혼합후 | 기준 | 판정
  - 대기질/소음: 지점/거리 | 오염물질 | 기여농도 | 현황 | 합산 | 기준 | 판정
  - 초과 행 빨간 배경(_EXCEED_BG)
- PDF 동일 구조 적용 (`_pdf_add_section`, `_pdf_add_prediction_table` 신규)

#### 4. Pydantic 스키마 업데이트
- `schemas/section.py`: `ScaffoldSectionRead`에 `prediction_result: PredictionResultRead | None`, `prediction_narrative: str` 추가
- `api/v1/sections.py`: `_prediction_result_to_read()` 변환 헬퍼 추가, 두 scaffold 엔드포인트에 prediction 필드 포함

#### 5. 테스트 (26개 신규)
- `test_prediction_narrative.py`: 26개 테스트
  - TestAirPredictionNarrative: 7개 (가우시안 플룸 서술문)
  - TestNoisePredictionNarrative: 6개 (소음 서술문)
  - TestWaterPredictionNarrative: 6개 (수질 서술문)
  - TestUnsupportedSectionNarrative: 3개 (미지원 섹션 fallback)
  - TestScaffoldPredictionIntegration: 4개 (통합 검증)

### 마이그레이션
- 불필요: 신규 DB 컬럼 없음 (prediction_result는 메모리 내 dataclass 필드)

### 주요 파일 (수정)
- `backend/app/services/draft_scaffold.py` — ScaffoldSection 확장 + 예측 통합
- `backend/app/services/narrative_generator.py` — generate_prediction_narrative 추가
- `backend/app/services/export_service.py` — N.4 영향 예측 소챕터 + 예측 테이블
- `backend/app/schemas/section.py` — prediction_result/prediction_narrative 필드 추가
- `backend/app/api/v1/sections.py` — prediction 변환 헬퍼 + 응답 필드 포함

### 주요 파일 (신규)
- `backend/tests/test_prediction_narrative.py` — 26개 테스트

### 전체 테스트
- 551개 전체 통과 (기존 525 + 신규 26)
