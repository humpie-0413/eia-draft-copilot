# Bootstrap Commands (Git Bash + Claude Code + shadcn/ui)

## 1. Create the repo
```bash
mkdir eia-draft-copilot
cd eia-draft-copilot
git init
```

## 2. Copy the project kit into the repo root
Copy the contents of this `for-claude/` package into the repository root.

## 3. Start Claude Code once in the project root
```bash
claude
```

Inside Claude Code:
```text
/rename phase-0-bootstrap
/help
/memory
```

## 4. Install everything-claude-code plugin
Inside Claude Code:
```text
/plugin marketplace add affaan-m/everything-claude-code
/plugin install everything-claude-code@everything-claude-code
```

Then in Git Bash:
```bash
git clone https://github.com/affaan-m/everything-claude-code.git ../everything-claude-code
cd ../everything-claude-code
./install.sh typescript python
cd ../eia-draft-copilot
```

## 5. Create the web app
```bash
pnpm create next-app@latest apps/web --yes
cd apps/web
pnpm dlx shadcn@latest init --base radix --yes
pnpm dlx skills add shadcn/ui
pnpm dlx shadcn@latest mcp init --client claude
cd ../..
```

## 6. Create the API app
```bash
uv init apps/api
cd apps/api
uv add "fastapi[standard]" sqlalchemy alembic psycopg[binary] pydantic-settings shapely pyproj geoalchemy2 lxml httpx pytest ruff mypy
cd ../..
```

## 7. Create local infra
Add a Postgres/PostGIS service via Docker Compose, then:
```bash
docker compose up -d
```

## 8. First Claude implementation prompt
```text
Read CLAUDE.md, docs/claude/phase-plan.md, docs/progress/NEXT_CHAT_BRIEF.md, and git status. Then implement Phase 0 only. Do not skip ahead.
```
