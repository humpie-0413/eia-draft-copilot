# 개발자 가이드

## 개발 환경 설정

### 사전 요구사항

| 도구 | 버전 | 용도 |
|------|------|------|
| Python | 3.12+ | 백엔드 |
| Node.js | 18+ | 프론트엔드 |
| PostgreSQL | 14+ | 데이터베이스 |
| PostGIS | 3.x | 공간 데이터 확장 |
| Docker | 최신 | PostgreSQL 실행 (권장) |

### 1. PostgreSQL + PostGIS 설정

**Docker (권장)**:
```bash
# 메인 DB
docker run -d \
  --name eia-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=eia_copilot \
  -p 5432:5432 \
  postgis/postgis:16-3.4

# 테스트 DB
docker exec eia-postgres psql -U postgres -c "CREATE DATABASE eia_copilot_test"
docker exec eia-postgres psql -U postgres -d eia_copilot_test -c "CREATE EXTENSION IF NOT EXISTS postgis"
```

### 2. 백엔드 설정

```bash
cd backend

# 가상환경 (선택)
python -m venv venv
source venv/Scripts/activate  # Windows (Git Bash)

# 의존성 설치
pip install -r requirements.txt

# 환경변수
cp .env.example .env
# .env 파일에서 DATABASE_URL, DATA_GO_KR_API_KEY 등 설정

# DB 마이그레이션
alembic upgrade head

# 개발 서버
uvicorn app.main:app --reload  # http://localhost:8000
```

### 3. 프론트엔드 설정

```bash
# 의존성 설치
npm install

# 환경변수 (선택)
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# 개발 서버
npm run dev  # http://localhost:3000
```

---

## 코드 컨벤션

### 파일 명명 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| React 컴포넌트 | PascalCase | `DraftEditor.tsx` |
| 유틸/훅 | camelCase | `useEiaDraft.ts`, `parseDocument.ts` |
| 타입 파일 | camelCase | `eiaDraft.ts` |
| API 라우트 | kebab-case | `src/app/api/data-sources/` |
| Python 모듈 | snake_case | `section_planner.py`, `qa_engine.py` |

### 코드 작성 규칙

- **한글 주석 허용**, 코드/변수명은 영문
- Python: Pydantic v2 스키마, SQLAlchemy 2.0 async 패턴
- TypeScript: 엄격(strict) 모드, Path alias `@/*`
- 커밋 메시지: 한글, 기능 단위로 분리

### 프론트엔드 규칙

- shadcn/ui 컴포넌트 활용 (`src/components/ui/`)
- API 호출은 `src/lib/` 클라이언트 함수를 통해서만
- 타입 정의는 `src/types/`에 집중
- 상태 관리: React 훅 (useState, useCallback, useEffect)

### 백엔드 규칙

- 모든 DB 연산은 async (`AsyncSession`)
- CRUD 함수는 `backend/app/crud/`에 위치
- 비즈니스 로직은 `backend/app/services/`에 위치
- API 엔드포인트는 `backend/app/api/v1/`에 위치
- 스키마(Pydantic)는 `backend/app/schemas/`에 위치

---

## 테스트 작성 및 실행

### 백엔드 테스트

```bash
cd backend
pytest tests/ -v                    # 전체 테스트
pytest tests/test_projects.py -v    # 프로젝트 테스트만
pytest tests/test_connectors.py -v  # 커넥터 테스트만
pytest tests/test_e2e.py -v         # E2E 테스트만
```

**테스트 DB 설정** (`conftest.py`):
- 테스트 DB URL: `postgresql+asyncpg://postgres:postgres@localhost:5432/eia_copilot_test?ssl=disable`
- 각 테스트 함수 실행 전 테이블 생성, 실행 후 삭제
- FastAPI 의존성 오버라이드로 테스트 DB 세션 주입

**테스트 작성 패턴**:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_something(client: AsyncClient):
    # 데이터 생성
    resp = await client.post("/api/v1/projects", json={"name": "테스트"})
    assert resp.status_code == 201

    # 검증
    data = resp.json()
    assert data["name"] == "테스트"
```

### 커넥터 실제 API 검증

```bash
# DATA_GO_KR_API_KEY가 설정되어 있어야 함
python scripts/test_connectors_live.py
```

이 스크립트는 실제 공공데이터 API를 호출하여 커넥터의 정상 동작을 확인합니다.

### 프론트엔드 테스트

```bash
npm run test  # Vitest
```

---

## Alembic 마이그레이션 관리

### 현재 마이그레이션 목록

| 번호 | 파일 | 내용 |
|------|------|------|
| 001 | `001_create_projects.py` | projects 테이블 + PostGIS 확장 |
| 002 | `002_create_evidence_tables.py` | data_sources, source_snapshots, evidences 테이블 |
| 003 | `003_create_similar_cases.py` | similar_cases 테이블 |

### 마이그레이션 명령어

```bash
cd backend

# 현재 마이그레이션 상태 확인
alembic current

# 최신 버전으로 업그레이드
alembic upgrade head

# 한 단계 업그레이드
alembic upgrade +1

# 한 단계 다운그레이드
alembic downgrade -1

# 새 마이그레이션 생성
alembic revision --autogenerate -m "설명"

# 마이그레이션 이력 조회
alembic history
```

### 새 마이그레이션 작성 절차

1. `backend/app/models/`에 새 모델 추가 또는 기존 모델 수정
2. `alembic revision --autogenerate -m "변경 설명"` 실행
3. 생성된 마이그레이션 파일을 검토 (PostGIS 관련 변경은 수동 확인 필요)
4. `alembic upgrade head`로 적용
5. 테스트 실행으로 검증

---

## 새 커넥터 추가 방법

### 1. 커넥터 클래스 작성

`backend/app/connectors/` 에 새 파일 생성:

```python
"""새 커넥터 설명."""

from app.connectors.base import BaseConnector
from app.schemas.evidence import EvidenceCreate

class NewConnector(BaseConnector):
    connector_key = "new_connector"
    display_name = "새 데이터 소스 이름"

    async def fetch(self, params: dict) -> dict:
        """외부 API를 호출하여 원본 데이터를 가져온다."""
        import httpx
        from app.config import settings

        async with httpx.AsyncClient(timeout=settings.CONNECTOR_TIMEOUT) as client:
            resp = await client.get("https://api.example.com/data", params=params)
            resp.raise_for_status()
            return resp.json()

    def normalize(
        self,
        raw_payload: dict,
        project_id,
        data_source_id,
        snapshot_id,
        screening_only=False,
    ) -> list[EvidenceCreate]:
        """원본 데이터를 EvidenceCreate 목록으로 정규화한다."""
        evidences = []
        for item in raw_payload.get("items", []):
            evidences.append(EvidenceCreate(
                project_id=project_id,
                snapshot_id=snapshot_id,
                data_source_id=data_source_id,
                category="카테고리",
                indicator="지표명",
                value=str(item["value"]),
                numeric_value=float(item["value"]),
                unit="단위",
                screening_only=screening_only,
            ))
        return evidences
```

### 2. 레지스트리 등록

`backend/app/connectors/registry.py`에서 자동 등록:

```python
from app.connectors.new_connector import NewConnector

register_connector(NewConnector())
```

### 3. 테스트 작성

`backend/tests/test_connectors.py`에 테스트 추가:

```python
class TestNewConnector:
    def test_normalize_basic(self):
        connector = NewConnector()
        raw = {"items": [{"value": 42}]}
        evidences = connector.normalize(raw, project_id, ds_id, snap_id)
        assert len(evidences) == 1
        assert evidences[0].indicator == "지표명"
```

### 4. 프론트엔드 연동 (선택)

`src/components/evidence/collect-data-dialog.tsx`에 새 커넥터의 파라미터 폼을 추가합니다.

---

## 새 QA 규칙 추가 방법

### 1. 규칙 함수 작성

`backend/app/services/qa_engine.py`에 규칙 함수 추가:

```python
def _rule_new_check(
    section_def: SectionDefinition,
    section_status: SectionStatus,
) -> QaIssue | None:
    """R006: 새 규칙 설명."""
    # 조건 검사
    if 정상_조건:
        return None

    return QaIssue(
        rule_id="R006",
        severity=Severity.WARNING,  # 또는 CRITICAL, INFO
        section_key=section_def.key,
        title=f"{section_def.title} 이슈 제목",
        message="상세 설명",
        indicators=["관련_지표"],
    )
```

### 2. run_qa에 규칙 등록

`run_qa()` 함수의 섹션 루프 내에 규칙 호출 추가:

```python
# R006: 새 규칙
issue = _rule_new_check(section_def, section_status)
if issue:
    all_issues.append(issue)
```

### 3. 규칙 ID 규칙

- 형식: `R{3자리 숫자}` (예: R001, R002, ..., R006)
- 심각도: `CRITICAL` (export 차단), `WARNING` (경고), `INFO` (참고)
- critical은 핵심 섹션(대기질, 수질, 소음·진동, 생태)에 대해서만 부여 권장

---

## 브랜치 전략 및 커밋 규칙

### 브랜치 구조

| 브랜치 | 용도 |
|--------|------|
| `main` | 안정 버전 |
| `feat/phase{N}-{설명}` | 기능 개발 (예: `feat/phase4-similar-cases`) |
| `fix/{설명}` | 버그 수정 |
| `docs/{설명}` | 문서 작업 |

### 커밋 규칙

```
{타입}: {한글 설명}

예시:
feat: 에어코리아 대기질 커넥터 실제 API 연동
fix: E2E 검증에서 발견된 3건의 버그 수정
test: 커넥터 연동 테스트 27개 추가
docs: Phase 6 완료 — 문서 업데이트
chore: Phase 0 — 프로젝트 스캐폴딩 및 기획
```

**타입 목록**:
| 타입 | 설명 |
|------|------|
| feat | 새 기능 추가 |
| fix | 버그 수정 |
| test | 테스트 추가/수정 |
| docs | 문서 작성/수정 |
| chore | 설정, 빌드 등 기타 |
| refactor | 리팩토링 (기능 변경 없음) |

### 의존성 관리

**백엔드** (`backend/requirements.txt`):
```
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
sqlalchemy[asyncio]>=2.0.30
asyncpg>=0.29.0
geoalchemy2>=0.15.0
alembic>=1.13.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
shapely>=2.0.4
geojson-pydantic>=1.1.0
python-dotenv>=1.0.1
httpx>=0.27.0
python-docx>=1.1.0
```

**프론트엔드** (`package.json`):
- Next.js ^14.2.0, React ^18.3.0
- shadcn/ui (Radix UI 기반)
- lucide-react (아이콘)
- tailwindcss ^3.4.4
