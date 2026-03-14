# EIA Draft Copilot

환경영향평가서(EIA) 초안 작성 및 품질검증(QA)을 지원하는 내부 B2B 도구입니다.
공공데이터 API로부터 환경 증거를 수집하고, 법정 11개 섹션에 대한 초안 뼈대를 자동 생성하며,
결정적 QA 규칙으로 품질을 검증한 뒤 DOCX/PDF 문서로 내보냅니다.

## 핵심 기능 흐름

```
프로젝트 입력 (이름, 유형, geometry)
  → 공공데이터 수집 (8종 커넥터: 대기질·수질·토양·기후·토지이용·문화재·교통량·폐기물 + 수동 입력)
  → 증거(Evidence) 정규화 및 저장
  → 유사사례 매칭 (사업유형/위치/규모/환경분야 가중 유사도)
  → 섹션 플래너 (11개 섹션 필수 지표 충족도 계산)
  → 통계 엔진 (지표별 기술 통계 산출)
  → 환경기준 비교 (대기/수질/소음/토양 기준 적합·초과 판정)
  → 영향 예측 (대기 확산 · 소음 전파 · 수질 혼합 — 3종 모델)
  → 서술문 템플릿 생성 (LLM 미사용 결정적 방식)
  → LLM 보강 (선택: OpenAI/Gemini adapter → DB 저장 → Export 반영)
  → QA 검증 (8개 규칙, critical/warning/info 등급 + 법적 필수 항목 검증)
  → DOCX/PDF export (표지 + 목차 + 본문 + 영향 예측 + 부록 3종)
```

### EIA 11개 섹션

| 순서 | 섹션 | 필수 지표 |
|------|------|-----------|
| 1 | 대기질 | PM10, PM2.5, NO2, SO2, CO, O3 |
| 2 | 수질 | BOD, COD, SS, T-N, T-P, DO |
| 3 | 토양 | Pb, Cd, pH, 유기물함량 |
| 4 | 소음·진동 | 소음 Leq(주간/야간), 진동 Lv(주간) |
| 5 | 생태 | 식물상 종수, 동물상 종수, 법정보호종, 비오톱 유형, 녹지자연도 |
| 6 | 토지이용 | 용도지역구분, 용도지구, 지목 |
| 7 | 교통 | 교통량 현황, 서비스수준 |
| 8 | 폐기물 | 폐기물 발생량, 폐기물 종류 |
| 9 | 경관 | 주요 조망점, 경관 유형 |
| 10 | 문화재 | 문화재명, 이격거리 |
| 11 | 기후 | 평균기온, 강수량, 평균풍속 |

### 공공데이터 커넥터 (8종)

| 커넥터 | 대상 API | 수집 지표 |
|--------|----------|-----------|
| `keco_air` | 에어코리아 대기오염정보 | PM10, PM2.5, O3, NO2, SO2, CO |
| `water_info` | 국립환경과학원 수질 DB | BOD, COD, SS, DO, T-N, T-P |
| `soil_info` | 국립환경과학원 토양측정망 | Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 |
| `kma_weather` | 기상청 ASOS 일자료 | 평균기온, 최고/최저기온, 강수량, 풍속, 습도 |
| `vworld_land_use` | V-world 2D데이터 | 용도지역구분, 용도지구, 지목 |
| `cultural_heritage` | 국가유산청 Open API | 문화재명, 종별, 이격거리, 소재지 |
| `traffic_volume` | 한국건설기술연구원 교통량 통계 | 교통량_현황(AADT), 도로등급, 도로명 |
| `waste_stats` | 행정안전부 생활쓰레기배출정보 | 생활폐기물_발생량, 음식물쓰레기_발생량, 재활용_발생량 |

### 영향 예측 모델 (3종)

| 모델 | 적용 섹션 | 설명 |
|------|----------|------|
| `gaussian_plume` | 대기질 | 가우시안 플룸 대기 확산 (PM10, PM2.5, NO2, SO2) — Pasquill-Gifford 확산계수 |
| `noise_propagation` | 소음·진동 | 점/선음원 거리감쇠 + Maekawa 차음벽 (주간/야간 Leq) |
| `water_mixing` | 수질 | 완전혼합 희석 모델 (BOD, COD, SS, T-N, T-P) |

> 예측 결과는 초안 뼈대(scaffold)에 자동 포함되며 DOCX/PDF 문서에도 반영됩니다.

### QA 규칙 (8개)

| ID | 규칙 | 심각도 |
|----|------|--------|
| R001 | 섹션 증거 없음 (사업유형 기반 동적 심각도) | critical/warning |
| R002 | 필수 지표 누락 (사업유형 기반 동적 심각도) | critical/warning |
| R003 | 충족도 50% 미만 | warning |
| R004 | 근거 없는 완료 상태 (unsupported claim) | critical |
| R005 | 단일 근거 지표 | info |
| R006 | 환경기준 초과 지표 | warning |
| R007 | 법적 필수 섹션 누락 (사업유형 기반) | critical |
| R008 | 법적 필수 지표 누락 (사업유형 기반) | warning |

> 사업유형이 설정되면 환경영향평가법 시행령 별표 3 기반으로 필수 섹션을 동적 판단합니다.

### LLM Adapter (3종)

| Adapter | 설명 | 모델 |
|---------|------|------|
| `none` | LLM 미사용 (기본값) | - |
| `openai_paid` | OpenAI GPT | gpt-4o-mini |
| `gemini_free` | Google Gemini | gemini-2.0-flash |

> MVP는 LLM 없이(`LLM_ADAPTER=none`) 완전 동작합니다.

### 법령 반영 기능

| 기능 | 설명 |
|------|------|
| 법적 근거 인용 | 서술문에 "환경정책기본법 시행령 별표 제1호에 따른…" 자동 삽입 |
| 사업유형별 평가 범위 | 12개 사업유형에 따라 필수/권장/선택 섹션 자동 분류 |
| 법적 필수 항목 검증 | QA R007/R008 규칙으로 법적 필수 섹션·지표 누락 자동 검출 |
| 환경기준 법적 근거 | 기준 비교 테이블에 법적 근거 열 (법령명·조문) 표시 |
| 지역구분별 기준 차등 | 소음 환경기준의 지역구분(가~라) 차등 적용 |
| DOCX/PDF 필수 표시 | 목차에 필수/선택 구분, 필수 미충족 섹션 강조 |

### 법령 데이터 모듈 (3개)

| 모듈 | 경로 | 역할 |
|------|------|------|
| `legal_references.py` | `backend/app/data/regulations/` | 환경기준별 법적 근거 매핑 |
| `required_items.py` | `backend/app/data/regulations/` | 사업유형별 필수 평가 항목 (12개 유형) |
| `area_classifications.py` | `backend/app/data/regulations/` | 소음 지역구분별 기준 차등 |

## 기술 스택

### 프론트엔드
- **프레임워크**: Next.js 14+ (App Router, TypeScript)
- **UI 라이브러리**: shadcn/ui (Radix UI 기반) + Tailwind CSS
- **아이콘**: lucide-react
- **테스트**: Vitest + React Testing Library

### 백엔드
- **프레임워크**: FastAPI (Python 3.12+)
- **데이터베이스**: PostgreSQL + PostGIS (공간 데이터)
- **ORM**: SQLAlchemy 2.0 (async) + GeoAlchemy2
- **마이그레이션**: Alembic
- **검증**: Pydantic v2 + geojson-pydantic
- **HTTP 클라이언트**: httpx (공공데이터 API 호출)
- **문서 생성**: python-docx (DOCX), reportlab (PDF)
- **LLM**: openai SDK + httpx (Gemini REST)
- **예측 모델**: 대기 확산(가우시안 플룸) + 소음 전파 + 수질 혼합
- **테스트**: pytest + httpx (ASGI 테스트, 605개)

## 로컬 개발 환경 설정

### 사전 요구사항

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+ (PostGIS 확장 포함)
- Docker (권장, PostgreSQL 실행용)

### 1. PostgreSQL + PostGIS (Docker)

```bash
docker run -d \
  --name eia-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=eia_copilot \
  -p 5432:5432 \
  postgis/postgis:16-3.4

# 테스트용 DB 생성
docker exec eia-postgres psql -U postgres -c "CREATE DATABASE eia_copilot_test"
docker exec eia-postgres psql -U postgres -d eia_copilot_test -c "CREATE EXTENSION IF NOT EXISTS postgis"
```

### 2. 환경변수 설정

**백엔드** (`backend/.env`):
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/eia_copilot
DEBUG=true
DATA_GO_KR_API_KEY=발급받은_인코딩_키
VWORLD_API_KEY=발급받은_V-world_키
CONNECTOR_TIMEOUT=30

# LLM adapter (선택, 기본값: none)
LLM_ADAPTER=none
# OPENAI_API_KEY=sk-...
# GOOGLE_API_KEY=AI...
```

**프론트엔드** (`.env.local`):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. 공공데이터포털 API 키 발급

커넥터를 통한 실제 데이터 수집에는 [공공데이터포털](https://www.data.go.kr/) API 키가 필요합니다.

1. 회원가입 및 로그인
2. 아래 API 활용 신청:
   - **에어코리아 대기오염정보**: https://www.data.go.kr/data/15073861/openapi.do
   - **국립환경과학원 수질 DB**: https://www.data.go.kr/data/15081073/openapi.do
   - **국립환경과학원 토양측정망**: https://www.data.go.kr/data/15056108/openapi.do
   - **기상청 ASOS 일자료**: https://www.data.go.kr/data/15059093/openapi.do
3. 발급받은 **인코딩 키**를 `backend/.env`의 `DATA_GO_KR_API_KEY`에 설정

> 5개 커넥터(keco_air, water_info, soil_info, kma_weather, traffic_volume)가 동일한 공공데이터포털 키를 사용합니다.
> waste_stats(폐기물) 커넥터도 공공데이터포털 키를 사용합니다.

### 4. V-world API 키 발급 (토지이용 커넥터)

1. [V-world](https://www.vworld.kr/) 회원가입 및 로그인
2. 오픈 API 인증키 발급
3. `backend/.env`의 `VWORLD_API_KEY`에 설정

> 국가유산청 문화재 커넥터는 API 키 없이 사용 가능합니다 (공개 API).

## 실행 방법

### 백엔드

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head          # DB 마이그레이션 실행
uvicorn app.main:app --reload # http://localhost:8000
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 프론트엔드

```bash
npm install
npm run dev                   # http://localhost:3000
```

### 통합 데모

```bash
# 백엔드 서버 실행 후
python scripts/demo_full_scenario.py
```

전체 워크플로우를 자동 실행합니다: 프로젝트 생성 → 8종 커넥터 수집 → 유사사례 매칭 → 통계 → 기준비교 → 서술문 → 영향 예측(3종) → LLM 보강 → QA → DOCX/PDF Export.

## 테스트

### 백엔드 테스트 (pytest, 605개)

```bash
cd backend
pytest tests/ -v
```

주요 테스트 파일:
- `tests/test_projects.py` — 프로젝트 CRUD + 헬스체크 (9개)
- `tests/test_connectors.py` — 커넥터 8종 fetch/normalize + 레지스트리 (95개)
- `tests/test_e2e.py` — 전체 워크플로우 E2E 테스트 (1개)
- `tests/test_spec_alignment.py` — 스펙 정렬 검증 (23개)
- `tests/test_statistics.py` — 통계 엔진 (16개)
- `tests/test_standard_checker.py` — 환경기준 비교 (27개)
- `tests/test_narrative_generator.py` — 서술문 생성기 (51개)
- `tests/test_prediction.py` — 대기 확산 예측 모델 (74개)
- `tests/test_prediction_noise_water.py` — 소음 전파 + 수질 혼합 (82개)
- `tests/test_prediction_narrative.py` — 예측 서술문 (26개)
- `tests/test_pred3_integration.py` — 예측 통합 (scaffold, export, API) (27개)
- `tests/test_export_format.py` — DOCX/PDF 포맷 (40+개)
- `tests/test_export_pdf.py` — PDF 출력 (4개)
- `tests/test_llm_adapter.py` — LLM adapter (29개)
- `tests/test_regulations.py` — 법령 데이터 + QA 규칙 + 평가 범위 (95개)

### 커넥터 실제 API 검증

```bash
python scripts/test_connectors_live.py
```

> `DATA_GO_KR_API_KEY`가 설정되어 있어야 합니다. V-world 토지이용 커넥터는 `VWORLD_API_KEY`도 필요합니다.

### 프론트엔드 테스트

```bash
npm run test                  # Vitest
```

## 프로젝트 디렉토리 구조

```
eia-draft-copilot/
├── src/                          # Next.js 프론트엔드
│   ├── app/                      # App Router 페이지
│   │   ├── layout.tsx            # 루트 레이아웃
│   │   ├── page.tsx              # 랜딩 페이지
│   │   └── projects/
│   │       ├── page.tsx          # 프로젝트 목록
│   │       └── [id]/
│   │           ├── evidences/    # Evidence Workbench
│   │           ├── sections/     # 섹션 플래너
│   │           ├── draft/        # 초안 뼈대 + 서술문
│   │           ├── qa/           # QA 결과
│   │           └── similar-cases/# 유사사례 매칭
│   ├── components/               # UI 컴포넌트
│   │   ├── evidence/             # 증거 (테이블, 폼, 필터, 수집, 수동 가이드)
│   │   ├── qa/                   # QA (이슈 목록, 요약바, Export, 미리보기)
│   │   ├── section/              # 섹션 (상태 카드, 초안 뷰, LLM 상태)
│   │   ├── similar-case/         # 유사사례 (매칭 테이블, 상세)
│   │   └── ui/                   # shadcn/ui 기본 컴포넌트
│   ├── lib/                      # API 클라이언트, 유틸리티
│   └── types/                    # TypeScript 타입 정의
├── backend/                      # FastAPI 백엔드
│   ├── app/
│   │   ├── api/v1/               # REST API 엔드포인트 (11개 라우터)
│   │   ├── connectors/           # 공공데이터 커넥터 (8종)
│   │   ├── crud/                 # DB CRUD 함수
│   │   ├── data/                 # 환경기준 데이터 + 법령 데이터
│   │   │   └── regulations/     # 법령 데이터 (법적 근거, 필수 항목, 지역구분)
│   │   ├── llm/                  # LLM adapter (3종)
│   │   ├── models/               # SQLAlchemy 모델
│   │   ├── schemas/              # Pydantic 스키마
│   │   ├── services/             # 비즈니스 로직 (통계, 기준비교, 서술문, QA, 평가범위, Export, 예측)
│   │   │   └── prediction/      # 영향 예측 모델 (대기 확산, 소음 전파, 수질 혼합)
│   │   ├── main.py               # FastAPI 앱 엔트리포인트
│   │   ├── config.py             # 환경 설정
│   │   └── db.py                 # DB 세션 관리
│   ├── alembic/                  # DB 마이그레이션 (4개)
│   ├── tests/                    # 백엔드 테스트 (605개)
│   └── requirements.txt          # Python 의존성
├── scripts/                      # 유틸리티 스크립트
│   ├── demo_full_scenario.py     # 통합 데모 (12단계, 예측 포함)
│   └── test_connectors_live.py   # 커넥터 실제 API 검증 (8종)
├── docs/                         # 문서
│   ├── architecture.md           # 시스템 아키텍처
│   ├── user-guide.md             # 사용자 가이드
│   ├── api-reference.md          # API 레퍼런스
│   ├── development.md            # 개발자 가이드
│   ├── claude/                   # Phase 계획, 아키텍처 결정
│   └── progress/                 # 작업 이력, 브리핑
└── public/                       # 정적 에셋
```

## 추가 문서

- [시스템 아키텍처](docs/architecture.md)
- [사용자 가이드](docs/user-guide.md)
- [API 레퍼런스](docs/api-reference.md)
- [개발자 가이드](docs/development.md)
- [Phase 계획](docs/claude/phase-plan.md)
- [법령 반영 Phase 계획](docs/regulation-phase-plan.md)
- [작업 이력](docs/progress/WORKLOG.md)
