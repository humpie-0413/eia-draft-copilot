# 시스템 아키텍처

## 전체 시스템 구성도

```
┌────────────────────────┐       ┌──────────────────────────────────┐
│   프론트엔드 (Next.js)  │       │        공공데이터 API             │
│   http://localhost:3000 │       │                                  │
│                        │       │  ┌──────────────────────────┐    │
│  ┌──────────────────┐  │       │  │ 에어코리아 (대기오염정보)  │    │
│  │ 프로젝트 목록     │  │       │  └──────────────────────────┘    │
│  │ Evidence 작업대   │  │       │  ┌──────────────────────────┐    │
│  │ 섹션 플래너       │  │  REST │  │ 국립환경과학원 (수질 DB)  │    │
│  │ 초안 뼈대 + 서술문│──┼──────▶│  └──────────────────────────┘    │
│  │ QA 결과 / Export  │  │       │  ┌──────────────────────────┐    │
│  │ 유사사례 매칭     │  │       │  │ 국립환경과학원 (토양측정망)│    │
│  │ LLM 상태 카드     │  │       │  └──────────────────────────┘    │
│  └──────────────────┘  │       │  ┌──────────────────────────┐    │
└────────────┬───────────┘       │  │ 기상청 (ASOS 일자료)     │    │
             │ REST API          │  └──────────────────────────┘    │
             ▼                   └────────────┬─────────────────────┘
┌──────────────────────────────────────────────┤ httpx
│                백엔드 (FastAPI)               │
│                http://localhost:8000          │
│                                              │
│  ┌──────────┐ ┌──────────────┐ ┌─────────────────────────────┐ │
│  │ API      │ │  서비스 계층   │ │    커넥터 파이프라인          │ │
│  │ 라우터   │─▶│              │ │ BaseConnector (8종 정의)     │ │
│  │ (13개)   │ │ ┌통계 엔진    │ │ ├─ KecoAirConnector    ✅   │ │
│  └──────────┘ │ ├기준비교     │ │ ├─ WaterInfoConnector  ✅   │ │
│               │ ├서술문생성   │ │ ├─ SoilInfoConnector   ⚠️   │ │
│               │ ├QA 규칙     │ │ ├─ KmaWeatherConnector ⚠️   │ │
│               │ ├평가범위     │ │ ├─ LandUseConnector    ⚠️   │ │
│               │ ├예측 엔진   │ │ ├─ CulturalHeritage    ✅   │ │
│               │ ├Export      │ │ ├─ TrafficVolume       ⚠️   │ │
│               │ └유사도 계산 │ │ └─ WasteStatsConnector ✅   │ │
│               └──────┬───────┘ └─────────────────────────────┘ │
│                      │          ┌────────────────────┐         │
│                      │          │  LLM Adapter        │         │
│                      │          │ ├─ NoneAdapter      │         │
│                      │          │ ├─ OpenAIAdapter    │         │
│                      │          │ └─ GeminiAdapter    │         │
│                      ▼          └────────────────────┘         │
│  ┌────────────────────────────────────────────────────────┐    │
│  │             CRUD 계층 (SQLAlchemy async)                │    │
│  └────────────────────────┬───────────────────────────────┘    │
└───────────────────────────┼────────────────────────────────────┘
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
              │  draft_narratives        │
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

5. 통계 엔진 (Post-1)
   └─ 섹션별·지표별 기술 통계 (평균, 최대, 최소, 표준편차, 기간)
   └─ 카테고리별 기본 연도 필터 (수질 5년, 대기 1년)

6. 환경기준 비교 (Post-2)
   └─ 대기/수질/소음/토양 환경기준 데이터 내장
   └─ 통계 결과 ↔ 기준 비교 → 적합/초과 판정
   └─ 수질 등급 판정 (Ia~V)

7. 섹션 상태 (Section Status)
   └─ 11개 섹션별 필수 지표 충족도 계산 (coverage_ratio)

8. 서술문 생성 (Post-3)
   └─ 섹션 유형별 서술문 템플릿 (대기/수질/소음/생태/범용)
   └─ LLM 미사용 결정적 방식

9. LLM 보강 (Post-6, 선택)
   └─ NoneAdapter: 원본 반환 / OpenAIAdapter / GeminiAdapter
   └─ 시스템 프롬프트: "한국 환경영향평가서 전문 작성자"
   └─ API 실패 시 fallback → 원본 반환
   └─ 보강 결과 DB 저장 (DraftNarrative) → Export 시 우선 사용 (Post-9)

10. 영향 예측 (Pred-1~2)
    └─ 섹션별 기본 모델 자동 선택
    └─ 배경 데이터 evidence에서 자동 추출
    ├─ 대기 확산: 가우시안 플룸 (Pasquill-Gifford 확산계수)
    ├─ 소음 전파: 점/선음원 거리감쇠 + Maekawa 차음벽
    └─ 수질 혼합: 완전혼합 희석 모델

11. 초안 뼈대 (Draft Scaffold, Pred-3)
    └─ 서술문 + 통계 요약 테이블 + 환경기준 비교 + 영향 예측 + 상세 데이터 샘플

12. QA (Quality Assurance)
    └─ 8개 결정적 규칙 실행 → critical/warning/info 이슈 목록
    └─ R007/R008: 사업유형 기반 법적 필수 항목 검증

13. Export (Post-5)
    └─ export_ready 확인 (critical 0건)
    └─ DOCX 5부 구조:
        ├─ 1부: 표지 (사업명, 사업유형, 위치, 작성일)
        ├─ 2부: 목차 (섹션별 상태 + 필수/선택 구분)
        ├─ 3부: 본문 11섹션 (서술문 + 통계 + 기준비교 + 상세 데이터)
        ├─ 4부: 영향 예측 (대기 확산, 소음 전파, 수질 혼합 — 해당 섹션만)
        └─ 5부: 부록 A(상세 데이터) + B(유사사례) + C(QA 결과)
    └─ PDF: 동일 구조 (reportlab)
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
├─── draft_narratives (LLM 보강 서술문) [project_id + section_key unique]
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

### draft_narratives 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | 고유 ID |
| project_id | UUID (FK) | 프로젝트 참조 (CASCADE) |
| section_key | VARCHAR(100) | 섹션 키 |
| narrative_text | TEXT | LLM 보강 서술문 |
| adapter_used | VARCHAR(100) | 사용된 LLM adapter |
| created_at | TIMESTAMPTZ | 생성일 |
| updated_at | TIMESTAMPTZ | 수정일 |

Unique 제약: (project_id, section_key)

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
| GET | `/connectors` | 사용 가능한 커넥터 목록 (8종) |
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

### 평가 범위 (Assessment Scope) — Reg-4

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/projects/{id}/assessment-scope` | 사업유형 기반 평가 범위 (필수/권장/선택) |

### 통계 (Statistics) — Post-1

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/projects/{id}/statistics` | 전체 섹션 통계 |
| GET | `/projects/{id}/statistics/{key}` | 개별 섹션 통계 |

### 환경기준 비교 (Standards Check) — Post-2

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/projects/{id}/standards-check` | 전체 섹션 환경기준 비교 |
| GET | `/projects/{id}/standards-check/{key}` | 개별 섹션 환경기준 비교 |

### QA

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/projects/{id}/qa` | QA 규칙 실행 결과 |
| GET | `/projects/{id}/qa/export-ready` | Export 가능 여부 확인 |

### Export — Post-5

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/projects/{id}/export/preview` | 문서 구조 미리보기 |
| POST | `/projects/{id}/export/docx` | DOCX 파일 다운로드 (부록 옵션) |
| GET | `/projects/{id}/export/pdf` | PDF 파일 다운로드 (부록 옵션) |

### LLM — Post-6

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/llm/status` | LLM adapter 상태 조회 |
| POST | `/llm/projects/{id}/enhance` | 섹션 서술문 AI 보강 |

### 영향 예측 (Predictions) — Pred-1~3

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/prediction-models` | 등록된 예측 모델 목록 + 입력 파라미터 |
| POST | `/projects/{id}/predict/{section_key}` | 섹션별 영향 예측 실행 |

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

### 구현된 커넥터 (8종 정의, 4종 운영 중)

| 커넥터 키 | 이름 | API | 수집 지표 | 상태 |
|-----------|------|-----|-----------|------|
| `keco_air` | 에어코리아 대기질 | ArpltnInforInqireSvc | PM10, PM2.5, O3, NO2, SO2, CO | ✅ 운영 중 |
| `water_info` | 수질 DB | WaterQualityService | BOD, COD, SS, DO, T-N, T-P | ✅ 운영 중 |
| `soil_info` | 토양측정망 | 토양측정정보 조회 | Cd, Cu, Pb, Zn, Ni, Cr6+, pH, 유기물함량 | ⚠️ 서버 오류 |
| `kma_weather` | 기상청 ASOS | 지상일자료 조회 | 기온, 강수량, 풍속, 습도 | ⚠️ 키 미승인 |
| `vworld_land_use` | V-world 토지이용 | 2D데이터 API (geomFilter) | 용도지역구분, 용도지구, 지목 | ⚠️ 키 미설정 |
| `cultural_heritage` | 국가유산청 문화재 | Open API (XML) | 문화재명, 종별, 이격거리, 소재지 | ✅ 운영 중 |
| `traffic_volume` | 교통량 통계 | 한국건설기술연구원 교통량 통계 | 교통량_현황(AADT), 도로등급, 도로명 | ⚠️ 엔드포인트 폐지 |
| `waste_stats` | 폐기물 배출정보 | 행정안전부 생활쓰레기배출정보 | 폐기물 배출일정/관리정보 (배출요일, 배출방법, 관리부서) | ✅ 운영 중 |

> **참고**: 폐기물 커넥터(`waste_stats`)는 폐기물 발생량이 아닌 배출 일정 및 관리 정보(배출요일, 배출방법, 관리부서 등)를 수집합니다.
> 4종(soil_info, kma_weather, vworld_land_use, traffic_volume)은 코드 구현이 완료되어 있으나 외부 요인으로 일시적으로 사용 불가합니다.

## 통계 엔진 구조 (Post-1)

```
calculate_section_statistics(db, project_id, section_key)
│
├── 대상: screening_only=False, numeric_value 있는 데이터
├── 카테고리별 기본 연도 필터:
│   ├── 수질: 최근 5년
│   ├── 대기: 최근 1년
│   └── 기타: 전체 기간
├── 지표별 기술 통계 계산:
│   ├── 평균 (mean)
│   ├── 최대값 (max_value)
│   ├── 최소값 (min_value)
│   ├── 표준편차 (std_dev)
│   ├── 건수 (count)
│   └── 기간 (period_start, period_end)
└── 일평균 집계 옵션 (시간별 → 일평균)
```

## 환경기준 비교 구조 (Post-2)

```
check_section_standards(db, project_id, section_key)
│
├── 환경기준 데이터 (backend/app/data/env_standards.py):
│   ├── 대기: PM10(50ug/m3), PM2.5(25), SO2(0.02ppm), NO2(0.03), CO(9), O3(0.06)
│   ├── 수질: BOD/COD/SS/DO/T-P 등급 기준 (Ia~V)
│   ├── 소음: 주간 55dB, 야간 45dB
│   └── 토양: Cd(4mg/kg), Cu(150), Pb(200), Zn(300), Ni(100), Cr6+(5) — 1지역 우려기준
│
├── 판정:
│   ├── pass: 기준 이하 (DO는 기준 이상)
│   ├── fail: 기준 초과
│   └── na: 기준 없음
│
├── 수질 등급 판정: BOD/COD/DO/T-P 기반 최악 등급
└── 섹션별 기준 비교 서술문 자동 생성
```

## 영향 예측 엔진 구조 (Pred-1~3)

```
backend/app/services/prediction/
│
├── base.py                   # BasePredictionModel (추상 클래스)
│   ├── predict(parameters, background_data) → PredictionResult
│   ├── get_required_inputs() → list[InputParameter]
│   └── get_model_info() → ModelInfo
│
├── air_dispersion.py         # AirDispersionModel (가우시안 플룸)
│   ├── Pasquill-Gifford 확산계수 (A~F 등급)
│   ├── 예측 거리: 100, 200, 500, 1000, 2000, 5000 m
│   ├── 오염물질: PM10, PM2.5, NO2, SO2
│   └── 사업유형별 기본 배출량 및 굴뚝 높이
│
├── noise_propagation.py      # NoisePropagationModel (거리감쇠 + 차음벽)
│   ├── 점음원/선음원 거리감쇠 (구면파/원통파)
│   ├── Maekawa 차음벽 회절 감쇠
│   ├── 에너지 합산 (배경소음 + 예측소음)
│   └── 예측 거리: 10, 20, 50, 100, 200, 500 m
│
├── water_mixing.py           # WaterMixingModel (완전혼합)
│   ├── 완전혼합 공식: (Q_r·C_r + Q_d·C_d) / (Q_r + Q_d)
│   ├── 오염물질: BOD, COD, SS, T-N, T-P
│   └── 방류수 수질기준 (물환경보전법) 기반 기본값
│
└── registry.py               # 모델 레지스트리
    ├── get_model(model_name) → BasePredictionModel
    ├── get_default_model_for_section(section_key) → BasePredictionModel
    └── list_models() → list[ModelInfo]

모델 매핑:
  air_quality     → gaussian_plume
  noise_vibration → noise_propagation
  water_quality   → water_mixing
```

### 예측 결과 통합 흐름 (Pred-3)

```
1. Scaffold 생성 시 예측 자동 실행
   generate_draft_scaffold() → 각 섹션마다:
   ├── get_default_model_for_section(section_key) → model
   ├── _extract_background_data(section_key, entries) → background
   ├── model.predict(parameters={project_type}, background_data) → PredictionResult
   └── generate_prediction_narrative(section_key, prediction_result) → narrative

2. ScaffoldSection에 예측 결과 포함
   ├── prediction_result: PredictionResult | None
   └── prediction_narrative: str

3. DOCX/PDF 출력 시 예측 섹션 포함
   ├── N.4 영향 예측 (적용 모델 + 서술문 + 데이터 테이블)
   ├── 전제 조건 + 모델 한계
   └── 초과 행 빨간 배경 표시
```

## 서술문 생성기 구조 (Post-3)

```
generate_narrative(section_def, section_stats, section_check)
│
├── 섹션 유형별 서술문 템플릿:
│   ├── 대기질: 지표별 기준 비교 + 초과 시 저감대책
│   ├── 수질: BOD/COD 병합 + 등급 판정 + 기타 지표
│   ├── 소음·진동: 주간/야간 판정 + 방음대책
│   ├── 생태: 종수 + 녹지자연도 + 법정보호종
│   └── 범용: 토양/교통/폐기물 등
│
├── LLM 미사용: 결정적 템플릿 방식
└── 미수집 섹션: 고정 서술문 "현장조사 및 자료 수집이 필요하다"
```

## 법령 데이터 구조 (Reg-1~Reg-4)

```
backend/app/data/regulations/
│
├── legal_references.py         # 환경기준별 법적 근거 매핑
│   └── {indicator → {standard_value, legal_basis, law_name, article}}
│
├── required_items.py           # 사업유형별 필수 평가 항목
│   └── REQUIRED_BY_TYPE: {project_type → RequiredItems}
│   └── 12개 사업유형 정의:
│       power_plant, road, housing, industrial, tourism, port,
│       military, airport, dam, reclamation, railway, other
│
└── area_classifications.py     # 소음 지역구분별 기준 차등
    └── 가/나/다/라 지역 × 주간/야간 × 일반/도로변
```

### 평가 범위 서비스 (scope_service.py)

```
get_assessment_scope(project_type)
│
├── required_items.py에서 필수 섹션·지표 조회
├── 각 섹션을 required / recommended / optional로 분류
└── AssessmentScope 반환 (섹션별 scope + required_indicators)
```

### 법적 근거 반영 흐름

```
1. 환경기준 비교 (standard_checker.py)
   └── IndicatorCheckResult.legal_basis에 법적 근거 매핑

2. 서술문 생성 (narrative_generator.py)
   └── 기준 비교 서술 시 "환경정책기본법 시행령 별표 제1호에 따른…" 자동 삽입

3. DOCX/PDF export (export_service.py)
   └── 기준 비교 테이블에 법적 근거 열 추가
   └── 목차에 필수/선택 구분 열 추가
   └── 필수 섹션 본문에 법적 필수 안내 문장 삽입

4. QA (qa_engine.py)
   └── R007: 법적 필수 섹션에 증거 없으면 critical
   └── R008: 법적 필수 지표 누락 시 warning
```

## QA 규칙 엔진 구조

```
run_qa(db, project_id)
│
├── 프로젝트 조회 → project_type 확인
├── 사업유형 기반 필수 섹션 집합 결정
├── 각 섹션(11개)에 대해:
│   ├── calculate_section_status() → 충족 상태 계산
│   ├── R007: 법적 필수 섹션 누락 (사업유형 설정 시)
│   ├── R001: 섹션 비어 있음 검사 (법적 필수는 R007에서 처리)
│   ├── R008: 법적 필수 지표 누락 (사업유형 설정 시)
│   ├── R002: 필수 지표 누락 검사
│   ├── R003: 충족도 50% 미만 검사
│   ├── R004: unsupported claim 검출
│   ├── R005: 단일 근거 지표 정보
│   └── R006: 환경기준 초과 지표 경고 (Post-2)
│
├── 이슈 집계 → QaSummary (critical/warning/info 건수)
└── export_ready = (critical_count == 0)
```

심각도 등급:
- **critical**: Export 차단. 법적 필수 섹션 누락, 핵심 섹션 증거 부재, unsupported claim
- **warning**: Export 가능. 법적 필수 지표 누락, 비핵심 섹션 이슈, 충족도 부족, 환경기준 초과
- **info**: 참고 정보. 근거 1건인 지표 안내

## LLM Adapter 구조 (Post-6)

```
BaseLLMAdapter (추상 클래스)
│
├── enhance_narrative(EnhanceInput) → EnhanceResult
│   └─ 입력: 섹션 키/제목, 템플릿 서술문, 통계 요약, 기준비교 요약
│   └─ 출력: 보강된 서술문, 사용 adapter, fallback 여부
│
├── NoneAdapter (기본값)
│   └─ 템플릿 서술문 그대로 반환
│
├── OpenAIAdapter (LLM_ADAPTER=openai_paid)
│   ├─ 모델: gpt-4o-mini
│   ├─ OPENAI_API_KEY 환경변수
│   └─ API 실패 시 fallback
│
└── GeminiAdapter (LLM_ADAPTER=gemini_free)
    ├─ 모델: gemini-2.0-flash
    ├─ GOOGLE_API_KEY 환경변수
    └─ httpx REST 직접 호출 + fallback
```

시스템 프롬프트 규칙:
- 데이터 외 내용 추가 금지
- 수치 변경 금지
- 공식적 문체 유지
- 추측 금지

## Export 구조 (Post-5)

### DOCX 구조
```
1. 표지 페이지
   └─ "환경영향평가서 초안" + 사업명 + 사업유형(한글) + 위치 + 작성일

2. 목차
   └─ 테이블: 섹션 번호(제N장) + 제목 + 상태 + 증거 건수

3. 본문 섹션 (11개, 5부 구조)
   ├─ 가. 현황 및 영향 분석 (서술문)
   ├─ 나. 측정 현황 요약 (통계 테이블)
   ├─ 다. 환경기준 비교 (기준 비교 테이블)
   ├─ 라. 영향 예측 (예측 모델 + 서술문 + 데이터 테이블, 해당 섹션만)
   └─ 마. 측정 데이터 (대표 샘플 5건)

4. 부록
   ├─ A: 상세 측정 데이터 (섹션별 최대 50건)
   ├─ B: 유사사례 매칭 결과 (유사도 점수 테이블)
   └─ C: QA 검사 결과 (요약 + 이슈 목록)
```

### 테이블 디자인
- 헤더 배경: 연한 파란(#D6E4F0)
- 교차 행 배경: #F5F5F7
- 환경기준 초과 행: 연한 빨간(#FDE0DC)

### PDF 동일 구조
- reportlab 기반
- 동일한 표지/목차/머리말꼬리말/부록 구조
- 초과 행 빨간 배경, 헤더 색상 동일 적용
