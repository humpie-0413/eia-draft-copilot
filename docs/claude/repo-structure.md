# Repository Structure

```text
project-root/
├─ .claude/
│  ├─ settings.json
│  ├─ agents/
│  │  ├─ frontend-shadcn.md
│  │  ├─ backend-fastapi.md
│  │  ├─ geo-data-integrator.md
│  │  ├─ regulation-auditor.md
│  │  └─ qa-export-guard.md
│  └─ skills/
│     ├─ eia-reg-check/
│     ├─ evidence-contract/
│     ├─ source-smoke-test/
│     ├─ migration-guard/
│     ├─ export-gate/
│     └─ ui-assembly-shadcn/
├─ .mcp.json
├─ CLAUDE.md
├─ backend/               # FastAPI 백엔드
│  ├─ app/
│  │  ├─ api/v1/          # REST API 엔드포인트
│  │  ├─ connectors/      # 공공데이터 커넥터
│  │  ├─ crud/            # DB CRUD 함수
│  │  ├─ models/          # SQLAlchemy 모델
│  │  ├─ schemas/         # Pydantic 스키마
│  │  ├─ services/        # 비즈니스 로직
│  │  ├─ main.py
│  │  ├─ config.py
│  │  └─ db.py
│  ├─ alembic/            # DB 마이그레이션
│  ├─ tests/              # 백엔드 테스트
│  └─ requirements.txt
├─ src/                   # Next.js 프론트엔드
│  ├─ app/                # App Router pages & layouts
│  ├─ components/         # UI 컴포넌트
│  ├─ lib/                # API 클라이언트, 유틸
│  └─ types/              # TypeScript 타입
├─ docs/
│  ├─ claude/
│  │  ├─ locked-decisions.md
│  │  ├─ repo-structure.md
│  │  ├─ output-contracts.md
│  │  ├─ phase-plan.md
│  │  ├─ data-source-registry-template.md
│  │  └─ bootstrap-commands.md
│  └─ progress/
│     ├─ WORKLOG.md
│     └─ NEXT_CHAT_BRIEF.md
├─ scripts/               # 데모/유틸 스크립트
└─ public/                # 정적 에셋
```

## Frontend targets
- `src/app/`
- `src/components/`
- `src/lib/`

## Backend targets
- `backend/app/api/`
- `backend/app/models/`
- `backend/app/schemas/`
- `backend/app/services/`
- `backend/app/connectors/`
- `backend/alembic/`
