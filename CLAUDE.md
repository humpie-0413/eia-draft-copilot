# EIA Draft Copilot — 프로젝트 지침

환경영향평가 문헌조사 및 공간 데이터 전처리 자동화 도구 + 입지 환경 리스크 스크리닝.
등록된 EIA 업체를 위한 내부 B2B 소프트웨어이며, B2B SaaS 전환 가능한 구조.
자율 보고서 작성기가 **아닌** 실무자의 현황조사 및 초안 작성 효율을 높이는 보조 도구.

> **면책사항**: 본 시스템의 산출물은 법적 효력이 없으며, 실무자의 최종 검토가 필수입니다.
> 산출물의 오류로 인한 평가서 반려 시 사용자(대행업체) 책임입니다.
> 전문 3D 모델링(AERMOD, CALPUFF 등)을 대체하지 않으나, **AERMOD 입력 파일 생성을 지원**합니다.
> 영향 예측은 기초 스크리닝 수준이며, 정밀 모사에는 전문 소프트웨어가 필요합니다.

참조:
- @docs/claude/locked-decisions.md
- @docs/claude/output-contracts.md

## 핵심 원칙

1. **Evidence First** — 증거 없으면 텍스트 생성 금지. 미해결(unresolved)로 표시
2. **Unsupported Claim 금지** — 모든 사실적 주장(factual claim)은 evidence ID 연결 필수
3. **LLM은 선택사항** — MVP는 `LLM_MODE=none`으로 동작해야 함
4. **Critical QA 이슈는 Export 차단** — 품질 게이트 우선

## Mission

1. 사업 부지에 대한 공공 증거(evidence) 수집 (9종 커넥터)
2. 유사 사례 가중 유사도 매칭
3. 법령 기반 필수 섹션 스캐폴드 및 증거 기반 초안 텍스트 준비
4. 환경 영향 예측 (대기 확산, 소음 전파, 수질 혼합)
5. 8개 QA 규칙으로 누락 항목, 근거 없는 주장, export 차단 이슈 감지
6. DOCX/PDF 산출물 생성
7. GIS 공간 분석 (버퍼/중첩) 및 5종 정적 도면 렌더링
8. 풍배도 생성 + AERMOD 기상 입력 파일 변환 (예정)

## 기술 스택

### 프론트엔드
- **Framework**: Next.js 14+ (App Router, TypeScript)
- **Styling**: Tailwind CSS
- **UI**: shadcn/ui (Radix UI 기반)
- **State**: React Context + useReducer
- **Map**: MapLibre GL JS (대화형 지도)
- **Testing**: Vitest + React Testing Library

### 백엔드
- **Framework**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL + PostGIS
- **ORM**: SQLAlchemy 2.0 (async) + GeoAlchemy2
- **Migration**: Alembic
- **Validation**: Pydantic v2 + geojson-pydantic
- **Export**: python-docx + WeasyPrint (DOCX/PDF)
- **GIS**: matplotlib + contextily (도면), Shapely/pyproj (공간 연산)
- **Testing**: pytest + httpx (649개 테스트)

### AI/LLM
- LLM 어댑터 3종: `none` (기본) / `openai_paid` / `gemini_free`
- MVP는 `LLM_MODE=none`으로 완전 동작

### 공간 분석 확장 (예정)
- rasterio (DEM 표고/경사도 분석)
- windrose (풍배도 생성)
- pyhwpx (HWP 출력, Windows 전용)
- AERMOD 기상 입력 파일 변환

## 시스템 구성 현황

### 백엔드 서비스 (13개)
| 서비스 | 역할 |
|--------|------|
| `section_planner.py` | 11개 섹션 정의 + 필수 지표 충족도 계산 + 평가 범위 연동 |
| `scope_service.py` | 사업유형별 필수/권장/선택 평가 범위 자동 판단 |
| `draft_scaffold.py` | 초안 뼈대 생성 (법적 근거 포함 서술문 우선 → 템플릿 fallback + 예측 결과 포함) |
| `statistics.py` | 지표별 기술 통계 (평균, 최대, 최소, 표준편차) |
| `standard_checker.py` | 대기/수질/소음/토양 환경기준 비교 + 등급 판정 + 법적 근거 |
| `narrative_generator.py` | 섹션별 서술문 템플릿 + 법적 근거 자동 삽입 + 예측 서술문 + 수동입력 가이드 |
| `similarity.py` | 유사사례 가중 유사도 계산 |
| `qa_engine.py` | 8개 QA 규칙 (R001~R008) + 사업유형 기반 동적 판단 + 부분충족 WARNING |
| `export_service.py` | DOCX/PDF 생성 + 법적 근거 열 + 필수 섹션 표시 + 영향 예측 섹션 + **GIS 도면 삽입** |
| `prediction/` | 예측 모듈 — 가우시안 플룸(대기), 소음 거리감쇠, 수질 완전혼합 |
| `llm/` | LLM 어댑터 계층 — none / openai_paid / gemini_free |
| `spatial_analysis.py` | 버퍼 분석 (EPSG:5179 변환) + 규제 항목 중첩 탐색 |
| `map_renderer.py` | 5종 정적 도면 렌더링 (위치도, 토지이용, 측정소, 소음등고선, 대기확산) |

### 커넥터 (9종) — 실측 기반 현황 (2026-03-16)
| 커넥터 | API | API 키 | 실측 상태 | 비고 |
|--------|-----|--------|-----------|------|
| 에어코리아 대기질 | data.go.kr | `DATA_GO_KR_API_KEY` | **안정 가동** | 138건/회 |
| 국립환경과학원 수질DB | data.go.kr | `DATA_GO_KR_API_KEY` | 타임아웃 빈발 | API 응답 느림, 디버깅 필요 |
| 토양측정망 | data.go.kr | `DATA_GO_KR_API_KEY` | 외부 장애 | HTTP 500 지속 |
| 기상청 ASOS | data.go.kr | `DATA_GO_KR_API_KEY` | 타임아웃 빈발 | API 응답 느림, 디버깅 필요 |
| V-world 토지이용 | vworld.kr | `VWORLD_API_KEY` | 지역 의존 | 양평 성공, 세종/보령 실패 |
| 토지이용규제정보 | data.go.kr | `DATA_GO_KR_API_KEY` | **안정 가동** | 2건/회 |
| 국가유산청 문화재 | khs.go.kr | 불필요 | 불안정 | 지역에 따라 0건 |
| 교통량 통계 | data.go.kr | `DATA_GO_KR_API_KEY` | 불안정 | 지역별 차이 |
| 폐기물 통계 | data.go.kr | `DATA_GO_KR_API_KEY` | 불안정 | 지역별 차이 |

> **실측 가동률**: 안정 2/9, 불안정 4/9, 장애 3/9

### 데모 검증 결과 (2026-03-16)
| 항목 | 양평 도로 (road) | 세종 택지 (housing) | 보령 발전소 (power_plant) |
|------|:----:|:----:|:----:|
| 커넥터 가동 | 5/9 | 3/9 | 2/9 |
| 총 증거 | 1,352건 | 248건 | 251건 |
| 예측 모델 | 3/3 | 3/3 | 3/3 |
| QA critical | 0 | 2 | 2 |
| Export 가능 | 예 | 아니오 | 아니오 |
| DOCX | 443KB | 486KB | 479KB |
| GIS 도면 | 5/5 | 5/5 | 5/5 |

### QA 규칙 (8개)
R001~R008: 법령 기반 동적 판단, 사업유형별 필수 지표 확인, 부분충족 WARNING 처리

### 영향 예측 모델 (3종)
- **대기 확산**: 가우시안 플룸 모델 (Gaussian Plume)
- **소음 전파**: 거리감쇠 모델 (Distance Attenuation)
- **수질 혼합**: 완전혼합 모델 (Complete Mixing)

### 법령 데이터 모듈 (3종)
- `legal_references.py` — 환경기준별 법적 근거 매핑 (환경정책기본법, 토양환경보전법 등)
- `required_items.py` — 사업유형/섹션별 필수 항목 정의
- `area_classifications.py` — 용도지역 분류 체계

### 섹션 상태 (7종)
| 상태 | 의미 |
|------|------|
| `auto_filled` | 구조화 입력 + 공공데이터로 자동 채움 완료 |
| `evidence_draft` | 증거 존재, 텍스트/해석 검토 필요 |
| `expert_required` | 전문가 판단 필요 |
| `procedure_pending` | 외부 절차 미완료 (미구현) |
| `not_applicable` | 해당 없음 |
| `partial` | 일부 지표 충족 |
| `empty` | 증거 0건 |

## 수정 완료 이력

| # | 문제 | 수정 내용 |
|---|------|-----------|
| 1 | 측정소명 접미사 자동 제거 | 양평군→양평 매칭 개선 |
| 2 | 부록 C QA 결과 누락 | export에 QA 부록 정상 포함 |
| 3 | 유사사례 유형별 필터링 | type_score > 0 조건 추가 |
| 4 | 환경기준 None 값 판정 | NaN/None 방어 로직, "N/A" 판정 |
| 5 | 대기확산 거리-농도 역전 | 사업유형별 굴뚝 높이 현실화 (도로 H=0m) |
| 6 | 폐기물 서술문 데이터 덤프 | 최빈값/대표값 요약형 개선, 중복 제거 |
| 7 | 수질 예측 결과 DOCX 미반영 | evidence 없어도 예측 결과 있으면 렌더링 |
| 8 | 경관 "환경기준 만족" 부적절 | 법적 기준 없는 섹션은 중립 표현 사용 |
| 9 | 폐기물 커넥터 과다 요청 | numOfRows=10 제한 |

## 디렉토리 구조

```
src/                           # Next.js 프론트엔드
  app/                         # App Router 페이지 & 레이아웃
    projects/                  # 프로젝트 관련 페이지
      [id]/evidences/          # 증거 목록
      [id]/sections/           # 섹션 상태/스캐폴드
      [id]/similar-cases/      # 유사사례
      [id]/qa/                 # QA 결과
      [id]/predictions/        # 영향 예측
      [id]/draft/              # 초안 미리보기
      [id]/map/                # 대화형 지도
      [id]/maps/               # GIS 도면 미리보기
  components/                  # UI 컴포넌트
    ui/                        # shadcn/ui 기본 컴포넌트
    map/                       # 지도 컴포넌트 (MapLibre GL JS)
    evidence/                  # 증거 관련 컴포넌트
    section/                   # 섹션 관련 컴포넌트
    similar-case/              # 유사사례 컴포넌트
    qa/                        # QA/Export 컴포넌트
  lib/                         # API 클라이언트, 유틸리티
  types/                       # TypeScript 타입 정의
backend/                       # FastAPI 백엔드
  app/
    api/v1/                    # REST API 엔드포인트 (15개 라우터)
    connectors/                # 공공데이터 커넥터 (9종 + base + registry)
    crud/                      # DB CRUD 함수
    data/                      # 참조 데이터
      env_standards.py         # 환경기준 데이터
      regulations/             # 법령 데이터 (3개 모듈)
        legal_references.py    # 법적 근거 매핑
        required_items.py      # 필수 항목 정의
        area_classifications.py # 용도지역 분류
    llm/                       # LLM 어댑터 (none, openai, gemini)
    models/                    # SQLAlchemy 모델
    schemas/                   # Pydantic 스키마
    services/                  # 비즈니스 로직
      prediction/              # 예측 모델 (대기, 소음, 수질)
    main.py                    # FastAPI 앱 엔트리포인트
    config.py                  # 환경 설정
    db.py                      # DB 세션 관리
  alembic/                     # DB 마이그레이션
  tests/                       # 백엔드 테스트 (649개)
docs/
  claude/                      # Phase 계획, 아키텍처 결정
  progress/                    # 작업 브리프, 진행 로그
  references/                  # EIA 참조 자료
scripts/
  demo_full_scenario.py        # 통합 데모 스크립트
  demo_road_yangpyeong.py      # 양평 도로 시나리오
  demo_housing_sejong.py       # 세종 택지 시나리오
  demo_powerplant_boryeong.py  # 보령 발전소 시나리오
  test_connectors_live.py      # 커넥터 실제 API 검증
output/                        # 생성된 DOCX/PDF 산출물
docker-compose.yml             # Docker Compose 기본 구성
docker-compose.dev.yml         # 개발 환경 오버라이드
docker-compose.prod.yml        # 운영 환경 오버라이드 (Nginx 포함)
Dockerfile                     # 프론트엔드 프로덕션 이미지
Dockerfile.dev                 # 프론트엔드 개발 이미지
nginx/
  default.conf                 # Nginx 리버스 프록시 설정
.github/
  workflows/
    ci.yml                     # CI 파이프라인 (테스트 + 빌드)
    deploy.yml                 # 배포 파이프라인 (이미지 푸시)
```

## API 엔드포인트

### 핵심 리소스 (`/api/v1`)
| 리소스 | 엔드포인트 | 메서드 |
|--------|-----------|--------|
| 프로젝트 | `/projects` | POST, GET |
| | `/projects/{id}` | GET, PATCH, DELETE |
| 데이터 소스 | `/data-sources` | POST, GET |
| | `/data-sources/{id}` | GET, PATCH, DELETE |
| 증거 | `/evidences` | POST, GET (필터: project_id, category, screening_only) |
| | `/evidences/{id}` | GET, PATCH, DELETE |
| 소스 스냅샷 | `/snapshots` | POST, GET (필터: project_id) |
| | `/snapshots/{id}` | GET, DELETE |
| 커넥터 | `/connectors` | GET (목록) |
| | `/connectors/{connector_key}/collect` | POST (수집 실행) |
| 유사사례 | `/similar-cases` | POST, GET |
| | `/similar-cases/{id}` | GET, PATCH, DELETE |
| | `/similar-cases/match/{project_id}` | GET (매칭) |

### 프로젝트별 기능 (`/api/v1/projects/{project_id}`)
| 기능 | 엔드포인트 | 설명 |
|------|-----------|------|
| 섹션 정의 | `/sections/definitions` | 11개 섹션 정의 조회 |
| 섹션 상태 | `/sections/status` | 전체 섹션 상태 |
| | `/sections/status/{section_key}` | 개별 섹션 상태 |
| 스캐폴드 | `/sections/scaffold` | 전체 초안 뼈대 |
| | `/sections/scaffold/{section_key}` | 개별 섹션 스캐폴드 |
| QA | `/qa` | QA 결과 (critical/warning/info) |
| | `/qa/export-ready` | Export 준비 상태 확인 |
| 평가 범위 | `/assessment-scope` | 사업유형별 평가 범위 |
| 통계 | `/statistics` | 프로젝트 전체 통계 |
| | `/statistics/{section_key}` | 섹션별 통계 |
| 환경기준 | `/standards-check` | 프로젝트 전체 기준 비교 |
| | `/standards-check/{section_key}` | 섹션별 기준 비교 |
| Export | `/export/preview` | 문서 구조 미리보기 |
| | `/export/docx` | DOCX 생성 (스트리밍) |
| | `/export/pdf` | PDF 생성 (스트리밍) |
| 예측 | `/predict/{section_key}` | 환경 영향 예측 실행 |
| 버퍼 분석 | `/spatial/buffer?radius=1000` | 버퍼 GeoJSON |
| 중첩 분석 | `/spatial/overlay?radius=1000` | 버퍼 내 규제 항목 |
| 도면 목록 | `/maps` | 사용 가능한 도면 유형 |
| 도면 렌더링 | `/maps/{map_type}` | 도면 PNG 반환 |

### 기타
| 엔드포인트 | 설명 |
|-----------|------|
| `/api/v1/prediction-models` | 사용 가능한 예측 모델 목록 |
| `/api/v1/llm/status` | LLM 어댑터 상태 |
| `/api/v1/llm/projects/{project_id}/enhance` | 섹션 서술문 LLM 강화 |
| `/health` | 헬스체크 |

## 환경변수

`backend/.env` 파일에 설정 (`backend/.env.example` 참조):

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 연결 문자열 | `postgresql+asyncpg://postgres:postgres@localhost:5432/eia_copilot` |
| `DATA_GO_KR_API_KEY` | 공공데이터포털 API 키 (에어코리아, 수질, 토양, 기상청, 교통량, 폐기물 공용) | *(필수)* |
| `VWORLD_API_KEY` | V-world API 키 (토지이용) — vworld.kr 별도 발급 | *(선택)* |
| `LLM_ADAPTER` | LLM 어댑터 선택 | `none` |
| `OPENAI_API_KEY` | OpenAI API 키 (LLM_ADAPTER=openai_paid 시) | *(선택)* |
| `GOOGLE_API_KEY` | Google Gemini API 키 (LLM_ADAPTER=gemini_free 시) | *(선택)* |
| `CONNECTOR_TIMEOUT` | 커넥터 API 호출 타임아웃 (초) | `60` |
| `DEBUG` | 디버그 모드 | `false` |

프론트엔드: `NEXT_PUBLIC_API_URL` (기본값 `http://localhost:3000`)

## 실행 방법

```bash
# 프론트엔드
npm run dev       # http://localhost:3000

# 백엔드
cd backend
pip install -r requirements.txt
alembic upgrade head              # DB 마이그레이션
uvicorn app.main:app --reload     # http://localhost:8000

# 테스트
cd backend
pytest tests/ -v                  # 649개 테스트

# 커넥터 실제 API 검증
python scripts/test_connectors_live.py

# 3종 시나리오 데모 (백엔드 서버 실행 후)
python scripts/demo_road_yangpyeong.py
python scripts/demo_housing_sejong.py
python scripts/demo_powerplant_boryeong.py
```

### Docker 실행 (권장)

```bash
# .env 설정
cp .env.docker.example .env
# .env 파일에 API 키 등 설정

# 개발 환경 (핫 리로드)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# 운영 환경 (Nginx 리버스 프록시 포함)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 사전 요구사항 (로컬 실행 시)
- PostgreSQL + PostGIS 로컬 설치
- Python 3.12+
- Node.js 18+
- `backend/.env` 설정 완료

## 코딩 규칙

- 컴포넌트: PascalCase (`DraftEditor.tsx`)
- 유틸/훅: camelCase (`useEiaDraft.ts`, `parseDocument.ts`)
- 타입 파일: camelCase (`eiaDraft.ts`)
- API 라우트: `src/app/api/` 하위에 kebab-case 폴더
- 커밋 메시지: 한글, conventional commits (`feat:`, `fix:`, `docs:`, `chore:`)
- 주석, 문서: 한글 작성
- 코드/변수명: 영문

## 아키텍처 제약

- LLM 어댑터 경계 유지: `none` / `openai_paid` / `gemini_free`
- MVP는 `LLM_MODE=none`으로 동작해야 함
- 외부 응답은 `source_snapshots`로 원본 보존
- 정규화된 증거는 raw payload와 분리 저장
- 지오메트리 저장 CRS: EPSG:4326
- `critical` QA 이슈는 export 차단
- 모든 사실적 주장(factual claim)은 evidence ID 연결 필수
- 증거 없으면 텍스트 생성 금지 → 미해결(unresolved)로 표시
- 비즈니스 로직은 services 모듈에. 페이지 컴포넌트에 넣지 말 것

## UI 제약

- shadcn/ui 전용. 다른 디자인 시스템 도입 금지
- 마케팅 사이트가 아닌, 내부 운영 도구 스타일
- Form + Zod + RHF (intake), Data Table + Tabs + Sheet (evidence)
- Tree + Badge + Card (section planning), Table + Alert + Dialog (QA)

## Codebase Priorities

1. 증거 파이프라인 정확성
2. 결정적 섹션 상태 계산
3. QA 신뢰성
4. 내부 전문가용 UI 명확성
5. 선택적 AI 연동은 최후순위

## 알려진 제한사항

- **공공 API 서버 장애/속도 문제**: 커넥터 가동률 변동 (실측 안정 가동 2/9)
- **API 데이터 지역 대표성**: 대상지 지역적 특수성을 대표하지 못할 수 있음 (평가자 정성적 판단 필수)
- **영향 예측은 기초 스크리닝 수준**: 전문 3D 모델링(AERMOD, CALPUFF 등) 대체 불가
- **AERMOD 입력 파일**: 생성만 지원, 실제 모델링은 전문 소프트웨어 필요
- **해양 분야 미커버**: MEIS OpenAPI 존재 여부 PoC 필요
- **소음·진동, 경관**: 현장조사 필수로 자동화 불가
- **생태자연도 속성 데이터**: API 쿼리 한계 (SHP/WMS 방식 필요)
- **산출물에 법적 효력 없음**: 실무자 최종 검토 필수
- **법적 책임**: 산출물의 오류로 인한 평가서 반려 시 사용자(대행업체) 책임
- **폐기물 커넥터**: 배출량이 아닌 배출일정 데이터 제공 (환경부 폐기물발생 API 별도 연동 필요)
- **V-world 지목 데이터**: 좌표에 따라 미반환 가능 (R002 WARNING으로 처리)
- **HWP 출력**: Windows 환경에서만 가능 (pyhwpx/win32com 제약)
- **DEM, 토지피복도 등 대용량 공간 데이터**: 로컬 저장소 필요
- **프론트엔드 프로젝트 생성 폼 미구현**: API를 통해서만 생성 가능
- **PROCEDURE_PENDING 상태 미구현**: 외부 절차 연동 필요
- **Draft claim contract 미구현**: LLM 연동 심화 시 구현 예정
- **실시간 협업, 테넌트 인증, 빌링 미지원**: MVP 비목표

## 미해결 이슈

- 수질 커넥터 타임아웃 근본 해결 (API 응답 시간 디버깅)
- 기상청 ASOS 타임아웃 근본 해결
- V-world 세종/보령 좌표 문제
- 폐기물/교통 지역별 안정성
- 토양측정망 외부 서버 장애 (수정 불가)
- "연평균의 연평균" 중복 표현 확인

## 다음 작업 계획 (통합 로드맵)

### Phase Connector-Fix: 커넥터 안정화 (최우선)
- 수질/기상청 API 응답 시간 디버깅 (python 직접 호출 테스트)
- numOfRows 제한 적용 확인
- V-world 좌표 문제 디버깅
- 3개 시나리오 모두 Export 가능 달성 목표

### Phase Wind-AERMOD: 풍배도 + AERMOD 입력 생성
- 기상청 ASOS 풍향/풍속 데이터 기반 Wind Rose 자동 생성
  - windrose 라이브러리 또는 matplotlib 극좌표 차트
  - 16방위 풍향빈도, 풍속구간별 빈도 시각화
  - PNG 도면으로 DOCX/PDF에 삽입
- AERMOD 기상 입력 파일 자동 변환
  - 지표기상 파일(.sfc): ASOS 데이터 → AERMOD 포맷
  - 상층기상 파일(.ua): 필요 시 라디오존데 연동 또는 기본값
  - 사용자가 다운로드하여 AERMOD 전문 소프트웨어에 입력
- 이 기능만으로 실무자에게 즉시 높은 가치 제공

### Phase Spatial-Advanced: 공간 분석 고도화
- SHP/GeoJSON 파일 업로드 지원 (현재 GeoJSON만)
- DEM 기반 표고/경사도 분석
  - rasterio + SRTM 30m 해상도 DEM
  - 사업 경계 내 최고/최저 표고, 평균 경사도 산출
  - 표고 단면도 생성
- 정밀 토지피복도 클리핑
  - 환경부 정밀 토지피복도(SHP) 활용
  - 사업 경계로 클리핑 → 피복 유형별 면적/비율 자동 산출
  - 표 + 원형 차트 자동 생성
- 연속지적도 중첩 분석
  - 사업 경계 내 지목별 편입 면적 자동 산출
  - "대 12,340㎡(45.2%), 전 8,760㎡(32.1%), 답 6,200㎡(22.7%)" 형식
  - DOCX에 지목별 면적 테이블 자동 삽입

### Phase HWP-Export: HWP 출력 (한국 실무 필수)
- pyhwpx 또는 win32com 기반 HWP 자동 생성
- 현재 DOCX export 구조를 HWP로 확장
- 환경영향평가서 표준 양식 적용
- 표지, 목차, 섹션별 서술문+테이블, 부록 구조 동일
- 산출물 3종: DOCX + PDF + HWP

### Phase Map-Enhancement: GIS 도면 사용자 친화성 개선
- contextily 배경지도 추가 (OpenStreetMap 타일)
- 도면 스타일 전문화 (반투명 도형, 윤곽선 라벨, 축척바, 방위표)
- 풍배도를 기후 섹션 도면으로 포함
- 해상도 200 DPI

### Phase Deploy: 배포 환경 구성 (보류 중, 지시 대기)
- Docker Compose (PostgreSQL+PostGIS, FastAPI, Next.js)
- CI/CD 파이프라인
- 환경 분리 (dev/staging/prod)

### Phase Portfolio: 포트폴리오 문서 정리
- GIS 도면 산출물 (배경지도 포함)
- 풍배도 + AERMOD 입력 파일 예시
- DEM 표고 분석 + 토지피복도 + 지적도 산출물
- 데이터 파이프라인 아키텍처 다이어그램
- Before/After 서술문 비교
- 법령 매핑 + QA 규칙 설계 설명
- 시스템 한계 명시

## 작업 규칙 (Working Rules)

- 편집 전 현재 phase와 상태 확인: `NEXT_CHAT_BRIEF.md`, `WORKLOG.md`, `git status`
- 작은 단위로 리뷰 가능한 변경
- 마이그레이션은 명시적으로. 숨은 스키마 변경 금지
- 비밀 보호: `.env`, `secrets/**`, `*.pem`, `*.key` 읽기 금지
- **커밋 시점은 Claude Code 에이전트가 자체 판단**
- **사용자에게 허가를 묻지 말고 프롬프트 범위 내 끝까지 완료**
- **더미 데이터 절대 사용 금지**
- **커밋 메시지, 주석, 문서는 한글로 작성**
- **curl 사용 금지 (python urllib 사용)**

## Claude Workflow

- `.claude/agents/` 하위 커스텀 서브에이전트 활용
- `.claude/skills/` 하위 프로젝트 스킬 활용
- 현재 phase와 무관한 작업이면 새 세션 권장
- 세션 종료 전 반드시 업데이트:
  - `docs/progress/WORKLOG.md`
  - `docs/progress/NEXT_CHAT_BRIEF.md`

## 완료 기준 (Done Criteria)

Phase 완료 조건:
1. 구현이 현재 phase 목표와 일치
2. 관련 테스트 통과
3. docs/progress 파일 업데이트 완료
4. 미해결 리스크 명시적 나열

## 전체 Phase 완료 현황

- Phase 0~6: MVP 완료 ✅
- Post-0.5 ~ Post-11: Post-MVP 개선 완료 ✅
- Reg-0~Reg-5: 법령 반영 완료 ✅
- Pred-1~Pred-3: 예측 모듈 통합 완료 ✅
- Conn-1~Conn-2: 커넥터 확장 완료 ✅
- Final-1~Final-2: 통합 검증 + 문서화 완료 ✅
- Demo-1~Demo-2: 통합 데모 + QA 해결 + Export 성공 ✅
- Doc-1: CLAUDE.md 전면 업데이트 ✅
- LLM-Enhancement: 서술문 품질 최종 개선 ✅
- GIS-1: GIS 공간 분석 및 도면 생성 ✅
- GIS-2: 프론트엔드 지도 시각화 ✅
- Demo-3: 3종 시나리오 데모 스크립트 ✅
- Deploy: 배포 환경 구성 (Docker Compose + CI/CD + 환경 분리) ✅
- Phase 4: 3종 시나리오 실행 검증 ✅
- Bugfix-6: 6건 버그 수정 (649개 테스트 통과) ✅

다음 작업 브리핑: `docs/progress/NEXT_CHAT_BRIEF.md` 참조
