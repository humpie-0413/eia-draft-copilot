# EIA Draft Copilot

환경영향평가(EIA) 초안 작성을 지원하는 AI 코파일럿 웹 애플리케이션.

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

## Phase Plan

전체 구현 계획은 `docs/claude/phase-plan.md` 참조.
다음 작업 브리핑은 `docs/progress/NEXT_CHAT_BRIEF.md` 참조.
