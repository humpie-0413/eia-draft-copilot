# Next Chat Brief

## 마지막 완료 Phase
**Phase 5: 섹션 플래너 + 초안 뼈대** ✅

## 완료된 작업 (Phase 5)

### 백엔드
- 섹션 정의 서비스 (`backend/app/services/section_planner.py`):
  - EIA 11개 섹션 정의 (대기, 수질, 토양, 소음·진동, 생태, 토지이용, 교통, 폐기물, 경관, 문화재, 기후)
  - 섹션별 필수 지표(required_indicators) 목록
  - evidence 기반 충족도(coverage_ratio) 계산: empty/partial/complete 상태 판정
  - screening_only=False인 본 평가 데이터만 대상
- 초안 뼈대 서비스 (`backend/app/services/draft_scaffold.py`):
  - evidence를 섹션별로 분류·배치
  - 지표별 그룹핑 + 정형화된 근거 나열 텍스트 생성
  - **unsupported claim 금지** — LLM 자유 작문 없이 evidence 데이터만 배치
- Pydantic 스키마 (`backend/app/schemas/section.py`):
  - SectionStatusRead, SectionStatusList — 섹션 상태 응답
  - EvidenceEntryRead, ScaffoldSectionRead, DraftScaffoldRead — 초안 뼈대 응답
- API 엔드포인트 (`backend/app/api/v1/sections.py`):
  - GET `/projects/{id}/sections/definitions` — 섹션 정의 목록
  - GET `/projects/{id}/sections/status` — 전체 섹션 충족 상태
  - GET `/projects/{id}/sections/status/{key}` — 개별 섹션 상태
  - GET `/projects/{id}/sections/scaffold` — 전체 초안 뼈대
  - GET `/projects/{id}/sections/scaffold/{key}` — 개별 섹션 뼈대

### 프론트엔드
- TypeScript 타입 (`src/types/section.ts`):
  - SectionStatus, SectionStatusList, DraftScaffold, ScaffoldSection, EvidenceEntry
- API 클라이언트 (`src/lib/section-api.ts`):
  - 섹션 정의/상태/초안 뼈대 조회 함수
- 컴포넌트:
  - SectionStatusCard — 충족도 바 + 지표 충족 목록 카드
  - ScaffoldSectionView — 근거 항목 테이블 + evidence 기반 요약문
- 페이지:
  - `/projects/[id]/sections` — 섹션 플래너 (통계 + 상태 카드 그리드)
  - `/projects/[id]/draft` — 초안 뼈대 (좌측 네비 + 근거 배치 뷰)
- 프로젝트 목록에 섹션 플래너 버튼 추가

## 이전 완료 Phase
- Phase 0: 스캐폴딩 ✅
- Phase 1: Project CRUD & Backend API ✅
- Phase 2: 데이터 커넥터 & Evidence 인프라 ✅
- Phase 3: Evidence Workbench UI ✅
- Phase 4: 유사사례 매칭 시스템 ✅

## 다음 작업: Phase 6
- QA 규칙 엔진 (필수 항목 체크, 법규 준수 검증)
- export gate (출력 전 검증)
- DOCX/PDF 출력
- AI 연동 (Claude API) — 섹션별 프롬프트 + 스트리밍 응답
- 커넥터 실제 API 호출 구현 (httpx 기반)

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
### Phase 5 신규 파일
- `backend/app/services/section_planner.py` — 섹션 정의 + 상태 계산
- `backend/app/services/draft_scaffold.py` — 초안 뼈대 생성
- `backend/app/schemas/section.py` — Pydantic 스키마
- `backend/app/api/v1/sections.py` — API 엔드포인트
- `src/types/section.ts` — TypeScript 타입
- `src/lib/section-api.ts` — API 클라이언트
- `src/components/section/section-status-card.tsx` — 섹션 상태 카드
- `src/components/section/scaffold-section-view.tsx` — 뼈대 섹션 뷰
- `src/app/projects/[id]/sections/page.tsx` — 섹션 플래너 페이지
- `src/app/projects/[id]/draft/page.tsx` — 초안 뼈대 페이지

### 기존 파일 수정
- `backend/app/main.py` — sections 라우터 등록
- `src/app/projects/page.tsx` — 섹션 플래너 버튼 추가
