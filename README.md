# EIA Draft Copilot

환경영향평가서(EIA) 초안 작성 및 품질검증(QA)을 지원하는 내부 도구입니다.
공공데이터 API로부터 환경 증거를 수집하고, 법정 11개 섹션에 대한 초안 뼈대를 자동 생성하며,
결정적 QA 규칙으로 품질을 검증한 뒤 DOCX 문서로 내보냅니다.

## 핵심 기능 흐름

```
프로젝트 입력 (이름, 유형, geometry)
  → 공공데이터 수집 (에어코리아 대기질 · 국립환경과학원 수질DB)
  → 증거(Evidence) 정규화 및 저장
  → 유사사례 매칭 (사업유형/위치/규모/환경분야 가중 유사도)
  → 섹션 플래너 (11개 섹션 필수 지표 충족도 계산)
  → 초안 뼈대 생성 (evidence 기반, unsupported claim 금지)
  → QA 검증 (5개 규칙, critical/warning/info 등급)
  → DOCX export (critical 이슈 시 차단)
```

### EIA 11개 섹션

| 순서 | 섹션 | 필수 지표 |
|------|------|-----------|
| 1 | 대기질 | PM10, PM2.5, NO2, SO2, CO, O3 |
| 2 | 수질 | BOD, COD, SS, T-N, T-P, DO |
| 3 | 토양 | 중금속(납, 카드뮴), 유류오염(TPH), pH |
| 4 | 소음·진동 | 소음 Leq(주간/야간), 진동 Lv(주간) |
| 5 | 생태 | 식물상 종수, 동물상 종수, 법정보호종, 비오톱 유형, 녹지자연도 |
| 6 | 토지이용 | 용도지역, 토지피복, 개발면적 |
| 7 | 교통 | 교통량 현황, 서비스수준 |
| 8 | 폐기물 | 폐기물 발생량, 폐기물 종류 |
| 9 | 경관 | 주요 조망점, 경관 유형 |
| 10 | 문화재 | 문화재 목록, 이격거리 |
| 11 | 기후 | 기온 연평균, 강수량 연평균, 풍향·풍속 |

### QA 규칙 (5개)

| ID | 규칙 | 심각도 |
|----|------|--------|
| R001 | 섹션 증거 없음 | 핵심 섹션 critical / 기타 warning |
| R002 | 필수 지표 누락 | 핵심 섹션 critical / 기타 warning |
| R003 | 충족도 50% 미만 | warning |
| R004 | 근거 없는 완료 상태 (unsupported claim) | critical |
| R005 | 단일 근거 지표 | info |

> 핵심 섹션: 대기질, 수질, 소음·진동, 생태

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
- **문서 생성**: python-docx (DOCX 출력)
- **테스트**: pytest + httpx (ASGI 테스트)

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
CONNECTOR_TIMEOUT=30
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
   - **국립환경과학원 수질 DB (물환경 수질측정망 운영결과)**: https://www.data.go.kr/data/15081073/openapi.do
3. 발급받은 **인코딩 키**를 `backend/.env`의 `DATA_GO_KR_API_KEY`에 설정

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

## 테스트

### 백엔드 테스트 (pytest)

```bash
cd backend
pytest tests/ -v              # 전체 테스트 실행 (37개+)
```

주요 테스트 파일:
- `tests/test_projects.py` — 프로젝트 CRUD + 헬스체크
- `tests/test_connectors.py` — 커넥터 fetch/normalize + 통합 (27개)
- `tests/test_e2e.py` — 전체 워크플로우 E2E 테스트

### 커넥터 실제 API 검증

```bash
cd backend
python ../scripts/test_connectors_live.py
```

> `DATA_GO_KR_API_KEY`가 설정되어 있어야 합니다.

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
│   │           ├── draft/        # 초안 뼈대
│   │           ├── qa/           # QA 결과
│   │           └── similar-cases/# 유사사례 매칭
│   ├── components/               # UI 컴포넌트
│   │   ├── evidence/             # 증거 관련 (테이블, 폼, 필터, 수집)
│   │   ├── qa/                   # QA (이슈 목록, 요약바, Export 버튼)
│   │   ├── section/              # 섹션 (상태 카드, 초안 뷰)
│   │   ├── similar-case/         # 유사사례 (매칭 테이블, 상세)
│   │   └── ui/                   # shadcn/ui 기본 컴포넌트
│   ├── lib/                      # API 클라이언트, 유틸리티
│   └── types/                    # TypeScript 타입 정의
├── backend/                      # FastAPI 백엔드
│   ├── app/
│   │   ├── api/v1/               # REST API 엔드포인트
│   │   ├── connectors/           # 공공데이터 커넥터
│   │   ├── crud/                 # DB CRUD 함수
│   │   ├── models/               # SQLAlchemy 모델
│   │   ├── schemas/              # Pydantic 스키마
│   │   ├── services/             # 비즈니스 로직
│   │   ├── main.py               # FastAPI 앱 엔트리포인트
│   │   ├── config.py             # 환경 설정
│   │   └── db.py                 # DB 세션 관리
│   ├── alembic/                  # DB 마이그레이션
│   ├── tests/                    # 백엔드 테스트
│   └── requirements.txt          # Python 의존성
├── scripts/                      # 유틸리티 스크립트
├── docs/                         # 문서
│   ├── architecture.md           # 시스템 아키텍처
│   ├── user-guide.md             # 사용자 가이드
│   ├── api-reference.md          # API 레퍼런스
│   ├── development.md            # 개발자 가이드
│   ├── claude/                   # Phase 계획
│   └── progress/                 # 작업 이력
└── public/                       # 정적 에셋
```

## 추가 문서

- [시스템 아키텍처](docs/architecture.md)
- [사용자 가이드](docs/user-guide.md)
- [API 레퍼런스](docs/api-reference.md)
- [개발자 가이드](docs/development.md)
- [Phase 계획](docs/claude/phase-plan.md)
- [작업 이력](docs/progress/WORKLOG.md)
