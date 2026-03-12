# EIA Draft Copilot — Project Instructions

한국 환경영향평가서 초안의 필수항목 자동채움 및 QA 엔진.
자율 보고서 작성기가 **아닌**, 등록된 EIA 업체를 위한 내부 B2B 도구.
MVP 대상 문서: **`환경영향평가서 초안`** 1종만.

참조:
- @docs/claude/locked-decisions.md
- @docs/claude/output-contracts.md

## Mission

1. 사업 부지에 대한 공공 증거(evidence) 수집
2. 유사 사례 매칭
3. 필수 섹션 스캐폴드 및 증거 기반 초안 텍스트 준비
4. 누락 항목, 근거 없는 주장, export 차단 이슈 감지

## Project Overview

- **목적**: 환경영향평가서 초안 작성 시 AI를 활용하여 작성 효율을 높이고, 법적 요건 충족을 지원
- **주요 기능**: EIA 섹션별 초안 생성, 참고문서 분석, 법규 체크리스트 검증
- **대상 사용자**: 환경영향평가 실무자, 환경 컨설턴트

## Tech Stack

### Frontend
- **Framework**: Next.js 14+ (App Router, TypeScript)
- **Styling**: Tailwind CSS
- **State**: React Context + useReducer (필요 시 Zustand 도입)
- **Testing**: Vitest + React Testing Library

### Backend
- **Framework**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL + PostGIS
- **ORM**: SQLAlchemy 2.0 (async) + GeoAlchemy2
- **Migration**: Alembic
- **Validation**: Pydantic v2 + geojson-pydantic
- **Testing**: pytest + httpx

### Shared
- **AI**: Anthropic Claude API

## Directory Structure

```
src/                   # Next.js 프론트엔드
  app/                 # App Router pages & layouts
  components/          # Reusable UI components
  lib/                 # Utility functions, API clients
  types/               # TypeScript type definitions
backend/               # FastAPI 백엔드
  app/
    api/v1/            # REST API 엔드포인트
    connectors/        # 공공데이터 커넥터 (fetch + normalize)
    crud/              # DB CRUD 함수
    models/            # SQLAlchemy 모델
    schemas/           # Pydantic 스키마
    main.py            # FastAPI 앱 엔트리포인트
    config.py          # 환경 설정
    db.py              # DB 세션 관리
  alembic/             # DB 마이그레이션
  tests/               # 백엔드 테스트
docs/
  claude/              # Phase plans, architecture decisions
  progress/            # Chat briefs, progress logs
  references/          # EIA reference materials
public/                # Static assets
```

## Conventions

- 컴포넌트: PascalCase (`DraftEditor.tsx`)
- 유틸/훅: camelCase (`useEiaDraft.ts`, `parseDocument.ts`)
- 타입 파일: camelCase (`eiaDraft.ts`)
- API 라우트: `src/app/api/` 하위에 kebab-case 폴더
- 커밋 메시지: 영문, conventional commits (`feat:`, `fix:`, `docs:`, `chore:`)
- 한글 주석 허용, 코드/변수명은 영문

## Commands

```bash
# Frontend
npm run dev       # 개발 서버 실행 (http://localhost:3000)
npm run build     # 프로덕션 빌드
npm run lint      # ESLint 검사
npm run test      # Vitest 테스트 실행

# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head              # DB 마이그레이션
uvicorn app.main:app --reload     # 개발 서버 (http://localhost:8000)
pytest tests/ -v                  # 테스트 실행
```

## 공공데이터 API 키 설정

커넥터를 통한 실제 데이터 수집에는 공공데이터포털 API 키가 필요합니다.

### 발급 방법
1. [공공데이터포털](https://www.data.go.kr/) 회원가입 및 로그인
2. 아래 API 활용 신청:
   - **에어코리아 대기오염정보**: https://www.data.go.kr/data/15073861/openapi.do
   - **국립환경과학원 수질 DB (물환경 수질측정망 운영결과)**: https://www.data.go.kr/data/15081073/openapi.do
3. 발급받은 인코딩 키를 `backend/.env`에 설정:
   ```
   DATA_GO_KR_API_KEY=발급받은_인코딩_키
   ```

### 커넥터 수집 API
- `POST /api/v1/connectors/{connector_key}/collect` — 데이터 수집 실행
- `GET /api/v1/connectors` — 사용 가능한 커넥터 목록

## Codebase Priorities

1. 증거 파이프라인 정확성
2. 결정적 섹션 상태 계산
3. QA 신뢰성
4. 내부 전문가용 UI 명확성
5. 선택적 AI 연동은 최후순위

## Architecture Constraints

- LLM 어댑터 경계 유지: `none` / `manual_prompt_pack` / `gemini_free` / `openai_paid` / `claude_paid`
- MVP는 `LLM_MODE=none`으로 동작해야 함
- 외부 응답은 `source_snapshots`로 원본 보존
- 정규화된 증거는 raw payload와 분리 저장
- 지오메트리 저장 CRS: EPSG:4326
- `critical` QA 이슈는 export 차단
- 모든 사실적 주장(factual claim)은 evidence ID 연결 필수
- 증거 없으면 텍스트 생성 금지 → 미해결(unresolved)로 표시

## UI Constraints

- shadcn/ui 전용. 다른 디자인 시스템 도입 금지
- 마케팅 사이트가 아닌, 내부 운영 도구 스타일
- Form + Zod + RHF (intake), Data Table + Tabs + Sheet (evidence)
- Tree + Badge + Card (section planning), Table + Alert + Dialog (QA)

## Working Rules

- 편집 전 현재 phase와 상태 확인: `NEXT_CHAT_BRIEF.md`, `WORKLOG.md`, `git status`
- 작은 단위로 리뷰 가능한 변경
- 마이그레이션은 명시적으로. 숨은 스키마 변경 금지
- 비즈니스 로직은 services 모듈에. 페이지 컴포넌트에 넣지 말 것
- 비밀 보호: `.env`, `secrets/**`, `*.pem`, `*.key` 읽기 금지

## Claude Workflow

- `.claude/agents/` 하위 커스텀 서브에이전트 활용
- `.claude/skills/` 하위 프로젝트 스킬 활용
- 현재 phase와 무관한 작업이면 새 세션 권장
- 세션 종료 전 반드시 업데이트:
  - `docs/progress/WORKLOG.md`
  - `docs/progress/NEXT_CHAT_BRIEF.md`

## Done Criteria

Phase 완료 조건:
1. 구현이 현재 phase 목표와 일치
2. 관련 테스트 통과
3. docs/progress 파일 업데이트 완료
4. 미해결 리스크 명시적 나열

## Phase Plan

전체 구현 계획은 `docs/claude/phase-plan.md` 참조.
다음 작업 브리핑은 `docs/progress/NEXT_CHAT_BRIEF.md` 참조.
