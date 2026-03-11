# Next Chat Brief

## 마지막 완료 Phase
**Phase 4: 유사사례(Similar Case) 매칭 시스템** ✅

## 완료된 작업 (Phase 4)

### 백엔드
- SimilarCase SQLAlchemy 모델 (사업 유형/위치/규모/환경분야/요약 등)
- Pydantic 스키마 (CRUD + 매칭 결과 응답 SimilarCaseMatchResult)
- Alembic 마이그레이션 003: similar_cases 테이블 + 사업유형/공간 인덱스
- CRUD 함수: 생성/조회/목록/수정/삭제 + 전체 조회(매칭용)
- 유사도 계산 서비스 (`backend/app/services/similarity.py`):
  - 사업 유형(0.35): 동일=1.0, 같은 그룹=0.5, 다름=0.0
  - 위치(0.25): centroid 간 haversine 거리 + 지수 감쇠 (50km→0.5)
  - 규모(0.20): min/max 면적 비율
  - 환경 분야(0.20): Jaccard 유사도 (증거 분야 교집합/합집합)
- API 엔드포인트:
  - CRUD: POST/GET/PATCH/DELETE `/api/v1/similar-cases`
  - 매칭: GET `/api/v1/similar-cases/match/{project_id}` (top_k, min_score)
  - 기존 evidence 데이터에서 환경 분야 자동 추출, geometry → ST_Area로 면적 추정

### 프론트엔드
- TypeScript 타입: SimilarCase, SimilarCaseMatch, SimilarCaseMatchList
- API 클라이언트: 목록 조회 + 매칭 검색 함수
- 매칭 결과 테이블 컴포넌트 (종합/항목별 유사도 점수 Badge 표시)
- 상세 시트 컴포넌트 (점수 바 시각화 + 기본정보/환경분야/요약/발견사항)
- 유사사례 페이지: `/projects/[id]/similar-cases`
- 프로젝트 목록에 유사사례 버튼 추가

## 이전 완료 Phase
- Phase 0: 스캐폴딩 ✅
- Phase 1: Project CRUD & Backend API ✅
- Phase 2: 데이터 커넥터 & Evidence 인프라 ✅
- Phase 3: Evidence Workbench UI ✅

## 다음 작업: Phase 5 이후
- Draft Editor UI (리치 텍스트 에디터, 섹션 네비게이션)
- AI 연동 (Claude API) — 섹션별 프롬프트 + 스트리밍 응답
- 커넥터 실제 API 호출 구현 (httpx 기반)
- Section planner, 초안 뼈대, QA, export 등

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
### Phase 4 신규 파일
- `backend/app/models/similar_case.py` — SimilarCase 모델
- `backend/app/schemas/similar_case.py` — Pydantic 스키마
- `backend/app/crud/similar_case.py` — CRUD 함수
- `backend/app/services/similarity.py` — 유사도 계산 서비스
- `backend/app/api/v1/similar_cases.py` — API 엔드포인트
- `backend/alembic/versions/003_create_similar_cases_table.py` — 마이그레이션
- `src/types/similar-case.ts` — TypeScript 타입
- `src/lib/similar-case-api.ts` — API 클라이언트
- `src/components/similar-case/similar-case-match-table.tsx` — 매칭 테이블
- `src/components/similar-case/similar-case-detail-sheet.tsx` — 상세 시트
- `src/app/projects/[id]/similar-cases/page.tsx` — 유사사례 페이지

### 기존 파일 수정
- `backend/app/models/__init__.py` — SimilarCase import 추가
- `backend/app/main.py` — similar_cases 라우터 등록
- `backend/alembic/env.py` — SimilarCase import 추가
- `src/app/projects/page.tsx` — 유사사례 버튼 추가
