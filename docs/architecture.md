# 시스템 아키텍처

## 전체 시스템 구성도

```
┌────────────────────────┐       ┌──────────────────────────┐
│   프론트엔드 (Next.js)  │       │      공공데이터 API       │
│   http://localhost:3000 │       │                          │
│                        │       │  ┌──────────────────┐    │
│  ┌──────────────────┐  │       │  │ 에어코리아        │    │
│  │ 프로젝트 목록     │  │       │  │ (대기오염정보)    │    │
│  │ Evidence 작업대   │  │       │  └──────────────────┘    │
│  │ 섹션 플래너       │  │  REST │  ┌──────────────────┐    │
│  │ 초안 뼈대 뷰어    │──┼──────▶│  │ 국립환경과학원    │    │
│  │ QA 결과 / Export  │  │       │  │ (수질 DB)        │    │
│  │ 유사사례 매칭     │  │       │  └──────────────────┘    │
│  └──────────────────┘  │       └────────────┬─────────────┘
└────────────┬───────────┘                    │
             │ REST API                       │ httpx
             ▼                                ▼
┌──────────────────────────────────────────────────────────┐
│                백엔드 (FastAPI)                           │
│                http://localhost:8000                      │
│                                                          │
│  ┌─────────┐ ┌─────────────┐ ┌────────────────────────┐ │
│  │ API     │ │  서비스 계층  │ │    커넥터 파이프라인     │ │
│  │ 라우터  │─▶│ (섹션/QA/   │ │ BaseConnector          │ │
│  │ (9개)   │ │ Export/유사) │ │ ├─ KecoAirConnector    │ │
│  └─────────┘ └──────┬──────┘ │ └─ WaterInfoConnector  │ │
│                      │        └────────────────────────┘ │
│                      ▼                                   │
│  ┌────────────────────────────────────────────────────┐  │
│  │             CRUD 계층 (SQLAlchemy async)            │  │
│  └────────────────────────┬───────────────────────────┘  │
└───────────────────────────┼──────────────────────────────┘
                            │ asyncpg
                            ▼
              ┌──────────────────────────┐
              │  PostgreSQL + PostGIS     │
              │                          │
              │  projects                │
              │  data_sources            │
              │  source_snapshots        │
              │  evidences               │
              │  similar_cases           │
              └──────────────────────────┘
```

## 데이터 흐름도

```
1. 수집 (Collect)
   POST /connectors/{key}/collect
   └─ fetch() → 외부 API 호출 (httpx)

2. 스냅샷 (Snapshot)
   └─ raw_payload (JSONB) 원본 보존 → source_snapshots 테이블

3. 정규화 (Normalize)
   └─ normalize() → 지표별 EvidenceCreate 목록 생성

4. 증거 (Evidence)
   └─ 벌크 INSERT → evidences 테이블 (카테고리/지표/값/단위)

5. 섹션 상태 (Section Status)
   └─ 11개 섹션별 필수 지표 충족도 계산 (coverage_ratio)

6. 초안 뼈대 (Draft Scaffold)
   └─ 섹션별 evidence 나열 + 요약 텍스트 생성 (LLM 없이)

7. QA (Quality Assurance)
   └─ 5개 결정적 규칙 실행 → critical/warning/info 이슈 목록

8. Export
   └─ export_ready 확인 (critical 0건) → python-docx로 DOCX 생성
```

## DB 스키마 개요

### 테이블 관계도

```
projects (프로젝트)
│
├─── evidences (증거) ──── source_snapshots (원본 스냅샷)
│       │                         │
│       └── data_sources ─────────┘
│           (데이터 소스)
│
└─── similar_cases (유사사례) [독립 테이블, 매칭 시 projects 참조]
```

### projects 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | 프로젝트 고유 ID |
| name | VARCHAR(255) | 프로젝트명 |
| description | TEXT | 설명 |
| project_type | VARCHAR(100) | 사업유형 (road, railway, power_plant 등 10종) |
| status | VARCHAR(50) | 상태 (draft, in_progress, review, completed, archived) |
| geometry | Geometry(SRID:4326) | 사업 부지 경계 (Polygon/MultiPolygon) |
| created_at | TIMESTAMPTZ | 생성일 |
| updated_at | TIMESTAMPTZ | 수정일 |

### data_sources 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | 데이터 소스 ID |
| name | VARCHAR(255) | 소스명 (unique) |
| connector_key | VARCHAR(100) | 커넥터 키 (unique) |
| base_url | VARCHAR(500) | 기본 URL |
| description | TEXT | 설명 |
| enabled | BOOLEAN | 활성 여부 |

### source_snapshots 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | 스냅샷 ID |
| data_source_id | UUID (FK) | 데이터 소스 참조 |
| project_id | UUID (FK) | 프로젝트 참조 |
| query_params | JSONB | 요청 파라미터 (재현 가능성) |
| raw_payload | JSONB | API 원본 응답 |
| status | VARCHAR(50) | 상태 (success, error, partial) |
| error_message | TEXT | 에러 메시지 |
| fetched_at | TIMESTAMPTZ | 수집 시점 |

### evidences 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | 증거 ID |
| project_id | UUID (FK) | 프로젝트 참조 (CASCADE) |
| snapshot_id | UUID (FK) | 스냅샷 참조 (SET NULL) |
| data_source_id | UUID (FK) | 데이터 소스 참조 (SET NULL) |
| category | VARCHAR(100) | 환경 분야 (12개 카테고리) |
| indicator | VARCHAR(200) | 지표명 (예: PM10_연평균, BOD) |
| value | VARCHAR(255) | 측정값 |
| numeric_value | FLOAT | 수치값 (파싱 가능한 경우) |
| unit | VARCHAR(50) | 단위 (예: ug/m3, mg/L, dB(A)) |
| observed_at | TIMESTAMPTZ | 관측 시점 |
| location | Point(SRID:4326) | 측정 위치 |
| metadata_json | JSONB | 추가 메타데이터 |
| screening_only | BOOLEAN | 스크리닝 전용 여부 |

인덱스: project_id, (project_id, screening_only), category, location (GiST)

### similar_cases 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | 유사사례 ID |
| name | VARCHAR(255) | 사례명 |
| project_type | VARCHAR(100) | 사업유형 |
| location | Geometry(SRID:4326) | 위치 (Point/Polygon/MultiPolygon) |
| area_sqm | FLOAT | 사업 면적 (m²) |
| completed_at | TIMESTAMPTZ | 완료일 |
| summary | TEXT | 평가 요약 |
| key_findings | JSONB | 주요 발견사항 (분야별) |
| evidence_categories | JSONB | 환경 분야 목록 |
| source_url | VARCHAR(500) | 출처 URL |
| metadata_json | JSONB | 추가 메타데이터 |

## API 엔드포인트 전체 목록

기본 경로: `/api/v1`

### 프로젝트 (Projects)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/projects` | 프로젝트 생성 |
| GET | `/projects` | 프로젝트 목록 조회 |
| GET | `/projects/{project_id}` | 프로젝트 상세 조회 |
| PATCH | `/projects/{project_id}` | 프로젝트 수정 |
| DELETE | `/projects/{project_id}` | 프로젝트 삭제 |

### 증거 (Evidences)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/evidences` | 증거 생성 |
| GET | `/evidences` | 증거 목록 (project_id 필수) |
| GET | `/evidences/{evidence_id}` | 증거 상세 |
| PATCH | `/evidences/{evidence_id}` | 증거 수정 |
| DELETE | `/evidences/{evidence_id}` | 증거 삭제 |

### 스냅샷 (Snapshots)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/snapshots` | 스냅샷 생성 |
| GET | `/snapshots` | 스냅샷 목록 (project_id 필수) |
| GET | `/snapshots/{snapshot_id}` | 스냅샷 상세 |
| DELETE | `/snapshots/{snapshot_id}` | 스냅샷 삭제 |

### 데이터 소스 (Data Sources)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/data-sources` | 데이터 소스 등록 |
| GET | `/data-sources` | 데이터 소스 목록 |
| GET | `/data-sources/connectors` | 등록된 커넥터 키 목록 |
| GET | `/data-sources/{source_id}` | 데이터 소스 상세 |
| PATCH | `/data-sources/{source_id}` | 데이터 소스 수정 |
| DELETE | `/data-sources/{source_id}` | 데이터 소스 삭제 |

### 커넥터 (Connectors)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/connectors` | 사용 가능한 커넥터 목록 |
| POST | `/connectors/{connector_key}/collect` | 데이터 수집 실행 |

### 유사사례 (Similar Cases)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/similar-cases` | 유사사례 등록 |
| GET | `/similar-cases` | 유사사례 목록 |
| GET | `/similar-cases/{case_id}` | 유사사례 상세 |
| PATCH | `/similar-cases/{case_id}` | 유사사례 수정 |
| DELETE | `/similar-cases/{case_id}` | 유사사례 삭제 |
| GET | `/similar-cases/match/{project_id}` | 프로젝트 유사사례 매칭 |

### 섹션 (Sections)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/projects/{id}/sections/definitions` | 섹션 정의 목록 (11개) |
| GET | `/projects/{id}/sections/status` | 전체 섹션 충족 상태 |
| GET | `/projects/{id}/sections/status/{key}` | 단일 섹션 충족 상태 |
| GET | `/projects/{id}/sections/scaffold` | 전체 초안 뼈대 |
| GET | `/projects/{id}/sections/scaffold/{key}` | 단일 섹션 초안 뼈대 |

### QA

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/projects/{id}/qa` | QA 규칙 실행 결과 |
| GET | `/projects/{id}/qa/export-ready` | Export 가능 여부 확인 |

### Export

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/projects/{id}/export/docx` | DOCX 파일 다운로드 |

### 헬스체크

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/health` | 서버 상태 확인 |

## 커넥터 파이프라인 구조

```
BaseConnector (추상 클래스)
│
├── fetch(params) → dict           # 1. 외부 API 호출 (httpx)
├── normalize(raw, ...) → list     # 2. 정규화 → EvidenceCreate 목록
└── collect(db, ...) → (snap, evs) # 3. 전체 파이프라인 실행
        │
        ├── fetch() 호출
        ├── SourceSnapshot 저장 (raw_payload 보존)
        ├── normalize() 호출
        └── Evidence 벌크 INSERT
```

### 구현된 커넥터

| 커넥터 키 | 이름 | API | 수집 지표 |
|-----------|------|-----|-----------|
| `keco_air` | 에어코리아 대기질 | 공공데이터포털 ArpltnInforInqireSvc | PM10, PM2.5, O3, NO2, SO2, CO |
| `water_info` | 국립환경과학원 수질 DB | 공공데이터포털 WaterQualityService | BOD, COD, SS, DO, T-N, T-P |

## QA 규칙 엔진 구조

```
run_qa(db, project_id)
│
├── 각 섹션(11개)에 대해:
│   ├── calculate_section_status() → 충족 상태 계산
│   ├── R001: 섹션 비어 있음 검사
│   ├── R002: 필수 지표 누락 검사
│   ├── R003: 충족도 50% 미만 검사
│   ├── R004: unsupported claim 검출
│   └── R005: 단일 근거 지표 정보
│
├── 이슈 집계 → QaSummary (critical/warning/info 건수)
└── export_ready = (critical_count == 0)
```

심각도 등급:
- **critical**: Export 차단. 핵심 4개 섹션(대기질, 수질, 소음·진동, 생태)의 증거 부재 또는 필수 지표 누락
- **warning**: Export 가능. 비핵심 섹션 이슈, 충족도 부족 등
- **info**: 참고 정보. 근거 1건인 지표 안내

## LLM Adapter 구조

현재 MVP는 LLM 없이 결정적(deterministic)으로 동작합니다.
향후 Phase에서 아래 adapter 구조로 LLM 연동을 계획하고 있습니다.

| Adapter | 설명 | 상태 |
|---------|------|------|
| `none` | LLM 미사용 (현재 기본값) | 활성 |
| `manual_prompt_pack` | 수동 프롬프트 패키지 | 계획 |
| `gemini_free` | Google Gemini (무료) | 계획 |
| `openai_paid` | OpenAI GPT (유료) | 계획 |
| `claude_paid` | Anthropic Claude (유료) | 계획 |

환경변수 준비:
- `OPENAI_API_KEY` — OpenAI 연동용
- `GOOGLE_API_KEY` — Google Gemini 연동용
- `ANTHROPIC_API_KEY` — Claude 연동용 (프론트엔드 `.env`)
