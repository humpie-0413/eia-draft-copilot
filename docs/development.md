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
- 환경기준 데이터는 `backend/app/data/`에 위치
- LLM adapter는 `backend/app/llm/`에 위치

---

## 테스트 작성 및 실행

### 백엔드 테스트

```bash
cd backend
pytest tests/ -v                         # 전체 테스트 (606개)
pytest tests/test_projects.py -v         # 프로젝트 테스트만
pytest tests/test_connectors.py -v       # 커넥터 테스트만
pytest tests/test_e2e.py -v              # E2E 테스트만
pytest tests/test_statistics.py -v       # 통계 엔진 테스트만
pytest tests/test_standard_checker.py -v # 환경기준 비교 테스트만
pytest tests/test_narrative_generator.py -v  # 서술문 생성기 테스트만
pytest tests/test_export_format.py -v    # 문서 포맷 테스트만
pytest tests/test_llm_adapter.py -v      # LLM adapter 테스트만
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

이 스크립트는 8개 커넥터의 실제 API 호출을 검증합니다.
현재 4종(keco_air, water_info, cultural_heritage, waste_stats)이 정상 운영 중이며,
4종(soil_info=서버 오류, kma_weather=키 미승인, vworld_land_use=키 미설정, traffic_volume=엔드포인트 폐지)은 일시적으로 사용 불가합니다.

### 통합 데모

```bash
# 백엔드 서버 실행 후
python scripts/demo_full_scenario.py
```

12단계 전체 흐름을 자동 실행하고 결과를 `output/` 폴더에 저장합니다.
더미 데이터를 사용하지 않으며, 실제 공공데이터 API 응답 기반으로 동작합니다 (소음/생태 분야만 수동 입력).

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
| 004 | `a2042f226531_add_draft_narratives...` | draft_narratives 테이블 (LLM 보강 서술문 저장) |

### 마이그레이션 명령어

```bash
cd backend

alembic current             # 현재 마이그레이션 상태
alembic upgrade head        # 최신 버전으로 업그레이드
alembic upgrade +1          # 한 단계 업그레이드
alembic downgrade -1        # 한 단계 다운그레이드
alembic revision --autogenerate -m "설명"  # 새 마이그레이션 생성
alembic history             # 마이그레이션 이력 조회
```

---

## 새 커넥터 추가 방법

### 현재 커넥터 현황 (8종 정의, 4종 운영 중)

| 커넥터 | 상태 | 비고 |
|--------|------|------|
| `keco_air` | ✅ 운영 중 | 공공데이터포털 API 키 |
| `water_info` | ✅ 운영 중 | 공공데이터포털 API 키 |
| `cultural_heritage` | ✅ 운영 중 | API 키 불필요 |
| `waste_stats` | ✅ 운영 중 | 공공데이터포털 API 키. 배출일정/관리 정보 수집 |
| `soil_info` | ⚠️ 일시 불가 | API 서버 오류 (500) |
| `kma_weather` | ⚠️ 일시 불가 | API 키 승인 대기 |
| `vworld_land_use` | ⚠️ 일시 불가 | VWORLD_API_KEY 미설정 |
| `traffic_volume` | ⚠️ 일시 불가 | API 엔드포인트 폐지 |

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

    def normalize(self, raw_payload, project_id, data_source_id, snapshot_id, screening_only=False):
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

`backend/app/connectors/registry.py`:
```python
from app.connectors.new_connector import NewConnector
register_connector(NewConnector())
```

### 3. 테스트 작성

`backend/tests/test_connectors.py`에 테스트 추가

### 4. 프론트엔드 연동 (선택)

`src/components/evidence/collect-data-dialog.tsx`에 새 커넥터의 파라미터 폼 추가

---

## 새 서비스 추가 방법

### 서비스 파일 구조

`backend/app/services/` 디렉토리에 위치:

| 파일 | 역할 |
|------|------|
| `section_planner.py` | 섹션 정의 + 충족도 계산 + 평가 범위 연동 |
| `scope_service.py` | 사업유형별 필수/권장/선택 평가 범위 판단 (Reg-4) |
| `draft_scaffold.py` | 초안 뼈대 생성 (LLM 서술문 우선 → 템플릿 fallback) |
| `statistics.py` | 지표별 기술 통계 (Post-1) |
| `standard_checker.py` | 환경기준 비교 + 법적 근거 (Post-2, Reg-2) |
| `narrative_generator.py` | 서술문 템플릿 생성 + 법적 근거 인용 (Post-3, Reg-2) |
| `similarity.py` | 유사사례 유사도 계산 |
| `qa_engine.py` | QA 규칙 엔진 (8개 규칙, R007/R008 포함) |
| `export_service.py` | DOCX/PDF 생성 + 법적 근거 열 + 필수 섹션 표시 + 영향 예측 |
| `prediction/` | 영향 예측 모델 (대기 확산 + 소음 전파 + 수질 혼합) |

### 새 서비스 추가 패턴

1. `backend/app/services/` 에 서비스 파일 작성
2. `backend/app/schemas/` 에 Pydantic 스키마 추가
3. `backend/app/api/v1/` 에 API 엔드포인트 추가
4. `backend/app/main.py` 에 라우터 등록
5. `backend/tests/` 에 테스트 추가

---

## 새 예측 모델 추가 방법

### 1. 모델 클래스 작성

`backend/app/services/prediction/` 에 새 파일 생성:

```python
"""새 예측 모델 설명."""

from app.services.prediction.base import (
    BasePredictionModel, PredictionResult, PredictionItem,
    ModelInfo, InputParameter,
)

class NewPredictionModel(BasePredictionModel):

    def predict(self, parameters: dict, background_data: dict | None = None) -> PredictionResult:
        """입력 파라미터와 배경 데이터로 예측 실행."""
        # 예측 로직 구현
        items = []
        for distance in [100, 200, 500]:
            items.append(PredictionItem(
                label=f"{distance}m",
                distance_m=float(distance),
                pollutant="지표명",
                predicted_concentration=계산값,
                background_concentration=배경값,
                total_concentration=합산값,
                unit="단위",
                standard_value=기준값,
                exceeds_standard=합산값 > 기준값,
            ))

        return PredictionResult(
            section_key="적용_섹션_키",
            model_name="model_name",
            input_parameters=parameters,
            predictions=items,
            summary="예측 요약문",
            assumptions=["전제 조건 1", "전제 조건 2"],
            limitations=["모델 한계 1"],
        )

    def get_required_inputs(self) -> list[InputParameter]:
        return [
            InputParameter(name="param1", display_name="파라미터 1",
                         unit="단위", default=기본값, required=False,
                         description="설명"),
        ]

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name="model_name",
            display_name="모델 표시 이름",
            description="모델 설명",
            applicable_sections=["적용_섹션_키"],
        )
```

### 2. 레지스트리 등록

`backend/app/services/prediction/registry.py`:
```python
from app.services.prediction.new_model import NewPredictionModel

# _MODEL_REGISTRY 딕셔너리에 추가
_MODEL_REGISTRY["model_name"] = NewPredictionModel()

# _SECTION_MODEL_MAP에 섹션 매핑 추가
_SECTION_MODEL_MAP["적용_섹션_키"] = ["model_name"]
```

### 3. 서술문 생성기 추가

`backend/app/services/narrative_generator.py`:
- `generate_prediction_narrative()` 에 새 섹션 키 분기 추가
- 예측 결과를 한글 서술문으로 변환하는 함수 작성

### 4. 테스트 작성

`backend/tests/` 에 테스트 추가:
- 모델 predict() 정확성 검증
- 레지스트리 조회 검증
- 서술문 생성 검증

---

## 새 QA 규칙 추가 방법

### 1. 규칙 함수 작성

`backend/app/services/qa_engine.py`에 추가:

```python
def _rule_new_check(section_def, section_status):
    """R007: 새 규칙 설명."""
    if 정상_조건:
        return None
    return QaIssue(
        rule_id="R007",
        severity=Severity.WARNING,
        section_key=section_def.key,
        title=f"{section_def.title} 이슈 제목",
        message="상세 설명",
        indicators=["관련_지표"],
    )
```

### 2. run_qa에 규칙 등록

`run_qa()` 함수의 섹션 루프 내에 규칙 호출 추가

### 3. 규칙 ID 규칙

- 형식: `R{3자리 숫자}` (예: R001~R008)
- 심각도: `CRITICAL` (export 차단), `WARNING` (경고), `INFO` (참고)
- 사업유형 설정 시 required_items.py 기반으로 동적 심각도 판단
- R007/R008은 법적 근거 필드(legal_basis) 포함

---

## 법령 데이터 수정/추가 방법 (Reg-1~Reg-4)

법령 데이터는 `backend/app/data/regulations/` 디렉토리에 Python 데이터 구조로 관리됩니다.

### 법적 근거 매핑 수정 (`legal_references.py`)

환경기준에 대한 법적 근거(법령명, 조문)를 매핑합니다.
`env_standards.py`의 `Standard` 클래스에 `legal_basis` 필드로 연동됩니다.

```python
# 새 법적 근거 추가 예시
LEGAL_REFS["새_지표명"] = LegalReference(
    indicator="새_지표명",
    standard_value=기준값,
    legal_basis="해당 법령명 및 조문",
    law_name="법령 약칭",
    article="조문 번호",
)
```

### 사업유형별 필수 항목 수정 (`required_items.py`)

12개 사업유형별 필수 평가 섹션과 지표를 정의합니다.

```python
# 새 사업유형 추가 예시
REQUIRED_BY_TYPE["new_type"] = RequiredItems(
    project_type="new_type",
    type_name="사업유형 한글명",
    legal_basis="환경영향평가법 시행령 별표 3 제X호",
    sections={
        "air_quality": ["PM10_연평균", "PM2.5_연평균"],
        "water_quality": ["BOD", "COD"],
        # ...
    },
)
```

변경 후 반드시 테스트 실행:
```bash
pytest tests/test_regulations.py -v
```

### 소음 지역구분 수정 (`area_classifications.py`)

소음환경기준의 지역구분별 기준값을 관리합니다.
현재 가/나/다/라 4개 지역 × 주간/야간 × 일반/도로변 구조입니다.

### 변경 시 영향 범위

| 파일 변경 | 영향받는 서비스 |
|-----------|----------------|
| `legal_references.py` | standard_checker, narrative_generator, export_service |
| `required_items.py` | scope_service, qa_engine (R007/R008), section_planner |
| `area_classifications.py` | standard_checker (소음 섹션) |

---

## LLM Adapter 추가 방법

### 1. adapter 클래스 작성

`backend/app/llm/` 에 새 파일 생성:

```python
from app.llm.base import BaseLLMAdapter, EnhanceInput, EnhanceResult

class NewAdapter(BaseLLMAdapter):
    @property
    def name(self) -> str:
        return "new_adapter"

    def is_available(self) -> bool:
        return bool(os.getenv("NEW_API_KEY"))

    async def enhance_narrative(self, input: EnhanceInput) -> EnhanceResult:
        if not self.is_available():
            return self._fallback(input)
        # LLM API 호출
        ...
```

### 2. factory 등록

`backend/app/llm/__init__.py`의 `get_llm_adapter()`에 분기 추가

### 3. 설정 추가

`backend/app/config.py`에 API 키 환경변수 추가

---

## 브랜치 전략 및 커밋 규칙

### 브랜치 구조

| 브랜치 | 용도 |
|--------|------|
| `main` | 안정 버전 |
| `feat/phase{N}-{설명}` | 기능 개발 |
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
```

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
reportlab>=4.0.0
openai>=1.0.0
```

**프론트엔드** (`package.json`):
- Next.js ^14.2.0, React ^18.3.0
- shadcn/ui (Radix UI 기반)
- lucide-react (아이콘)
- tailwindcss ^3.4.4
