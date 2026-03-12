# API 레퍼런스

기본 URL: `http://localhost:8000/api/v1`

Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

---

## 헬스체크

### GET /health

서버 상태를 확인합니다.

**응답 (200)**:
```json
{
  "status": "ok"
}
```

---

## 프로젝트 (Projects)

### POST /projects

프로젝트를 생성합니다.

**요청**:
```json
{
  "name": "○○ 도로건설사업",
  "description": "서울~수원 간 고속도로 건설",
  "project_type": "road",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [[126.97, 37.56], [126.98, 37.56], [126.98, 37.57], [126.97, 37.57], [126.97, 37.56]]
    ]
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| name | string | O | 프로젝트명 |
| description | string | X | 설명 |
| project_type | string | X | 사업유형 (road, railway, power_plant, industrial, housing, airport, port, dam, reclamation, other) |
| geometry | GeoJSON | X | 사업 부지 경계 (Polygon/MultiPolygon, EPSG:4326) |

**응답 (201)**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "○○ 도로건설사업",
  "description": "서울~수원 간 고속도로 건설",
  "project_type": "road",
  "status": "draft",
  "geometry": { "type": "Polygon", "coordinates": [...] },
  "created_at": "2026-03-12T10:00:00+09:00",
  "updated_at": "2026-03-12T10:00:00+09:00"
}
```

### GET /projects

프로젝트 목록을 조회합니다.

**쿼리 파라미터**:
| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| skip | int (≥0) | 0 | 건너뛸 항목 수 |
| limit | int (1-100) | 50 | 조회 항목 수 |

**응답 (200)**:
```json
{
  "items": [
    { "id": "...", "name": "...", "status": "draft", ... }
  ],
  "total": 1
}
```

### GET /projects/{project_id}

단일 프로젝트를 조회합니다.

**응답 (200)**: ProjectRead 객체
**응답 (404)**: `{ "detail": "Project not found" }`

### PATCH /projects/{project_id}

프로젝트를 수정합니다. 변경할 필드만 전송합니다.

**요청**:
```json
{
  "status": "in_progress",
  "description": "수정된 설명"
}
```

**응답 (200)**: 수정된 ProjectRead 객체

### DELETE /projects/{project_id}

프로젝트를 삭제합니다.

**응답 (204)**: 본문 없음

---

## 증거 (Evidences)

### POST /evidences

증거를 생성합니다.

**요청**:
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "category": "air_quality",
  "indicator": "PM10_연평균",
  "value": "42",
  "numeric_value": 42.0,
  "unit": "ug/m3",
  "observed_at": "2024-01-15T00:00:00+09:00",
  "screening_only": false,
  "metadata_json": { "station_name": "종로구" }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| project_id | UUID | O | 프로젝트 ID |
| category | string | O | 환경 분야 |
| indicator | string | O | 지표명 |
| value | string | O | 측정값 (문자열) |
| numeric_value | float | X | 수치값 |
| unit | string | X | 단위 |
| observed_at | datetime | X | 관측 시점 |
| location | GeoJSON Point | X | 측정 위치 |
| screening_only | bool | X | 스크리닝 전용 여부 (기본 false) |
| metadata_json | object | X | 추가 메타데이터 |
| snapshot_id | UUID | X | 스냅샷 참조 |
| data_source_id | UUID | X | 데이터 소스 참조 |

**카테고리 목록**: `air_quality`, `water_quality`, `noise_vibration`, `ecology`, `soil`, `waste`, `landscape`, `cultural_heritage`, `climate`, `land_use`, `traffic`, `other`

**응답 (201)**: EvidenceRead 객체

### GET /evidences

증거 목록을 조회합니다.

**쿼리 파라미터**:
| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| project_id | UUID | O | 프로젝트 ID |
| category | string | X | 분야 필터 |
| screening_only | bool | X | null이면 전체, true/false이면 필터 |
| data_source_id | UUID | X | 데이터 소스 필터 |
| skip | int (≥0) | X | 페이지네이션 |
| limit | int (1-100) | X | 페이지네이션 (기본 50) |

**응답 (200)**:
```json
{
  "items": [
    {
      "id": "...",
      "project_id": "...",
      "category": "air_quality",
      "indicator": "PM10_연평균",
      "value": "42",
      "numeric_value": 42.0,
      "unit": "ug/m3",
      "observed_at": "2024-01-15T00:00:00+09:00",
      "screening_only": false,
      "metadata_json": { "station_name": "종로구" },
      "created_at": "2026-03-12T10:00:00+09:00"
    }
  ],
  "total": 1
}
```

### GET /evidences/{evidence_id}

단일 증거를 조회합니다.

**응답 (200)**: EvidenceRead 객체
**응답 (404)**: `{ "detail": "Evidence not found" }`

### PATCH /evidences/{evidence_id}

증거를 수정합니다.

**요청**: 변경할 필드만 전송
**응답 (200)**: 수정된 EvidenceRead 객체

### DELETE /evidences/{evidence_id}

증거를 삭제합니다.

**응답 (204)**: 본문 없음

---

## 스냅샷 (Snapshots)

### POST /snapshots

스냅샷을 생성합니다.

**요청**:
```json
{
  "data_source_id": "...",
  "project_id": "...",
  "raw_payload": { "items": [...] },
  "query_params": { "station_name": "종로구" },
  "status": "success"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| data_source_id | UUID | O | 데이터 소스 ID |
| project_id | UUID | O | 프로젝트 ID |
| raw_payload | object | O | API 원본 응답 |
| query_params | object | X | 요청 파라미터 |
| status | string | X | 상태 (success/error/partial) |
| error_message | string | X | 에러 메시지 |

**응답 (201)**: SourceSnapshotRead 객체

### GET /snapshots

스냅샷 목록을 조회합니다.

**쿼리 파라미터**:
| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| project_id | UUID | O | 프로젝트 ID |
| data_source_id | UUID | X | 데이터 소스 필터 |
| skip | int | X | 페이지네이션 |
| limit | int | X | 페이지네이션 |

**응답 (200)**: `{ "items": [...], "total": N }`

### GET /snapshots/{snapshot_id}

단일 스냅샷을 조회합니다.

**응답 (200)**: SourceSnapshotRead 객체

### DELETE /snapshots/{snapshot_id}

스냅샷을 삭제합니다.

**응답 (204)**: 본문 없음

---

## 데이터 소스 (Data Sources)

### POST /data-sources

데이터 소스를 등록합니다.

**요청**:
```json
{
  "name": "에어코리아 대기질",
  "connector_key": "keco_air",
  "base_url": "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc",
  "description": "에어코리아 실시간 대기오염 정보",
  "enabled": true
}
```

**응답 (201)**: DataSourceRead 객체

### GET /data-sources

데이터 소스 목록을 조회합니다.

**쿼리 파라미터**:
| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| skip | int | 0 | 페이지네이션 |
| limit | int | 50 | 페이지네이션 |
| enabled_only | bool | false | 활성 소스만 조회 |

**응답 (200)**: `{ "items": [...], "total": N }`

### GET /data-sources/connectors

등록된 커넥터 키와 이름 목록을 조회합니다.

**응답 (200)**:
```json
[
  { "connector_key": "keco_air", "display_name": "한국환경공단 대기질 (에어코리아)" },
  { "connector_key": "water_info", "display_name": "국립환경과학원 수질 DB (물환경 수질측정망)" }
]
```

### GET /data-sources/{source_id}

**응답 (200)**: DataSourceRead 객체

### PATCH /data-sources/{source_id}

**요청**: 변경할 필드만 전송
**응답 (200)**: 수정된 DataSourceRead 객체

### DELETE /data-sources/{source_id}

**응답 (204)**: 본문 없음

---

## 커넥터 (Connectors)

### GET /connectors

사용 가능한 커넥터 목록을 조회합니다.

**응답 (200)**:
```json
[
  { "connector_key": "keco_air", "display_name": "한국환경공단 대기질 (에어코리아)" },
  { "connector_key": "water_info", "display_name": "국립환경과학원 수질 DB (물환경 수질측정망)" }
]
```

### POST /connectors/{connector_key}/collect

데이터 수집을 실행합니다. 외부 API를 호출하여 데이터를 가져오고, 정규화하여 증거로 저장합니다.

**경로 파라미터**: `connector_key` — 커넥터 식별 키 (예: `keco_air`, `water_info`)

**요청**:
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "params": {
    "station_name": "종로구",
    "data_term": "MONTH"
  },
  "screening_only": false
}
```

**커넥터별 파라미터**:

#### keco_air (에어코리아 대기질)
| 파라미터 | 필수 | 설명 |
|----------|------|------|
| station_name | O | 측정소명 (예: "종로구", "강남구") |
| data_term | X | 조회기간 (DAILY/MONTH/3MONTH, 기본 DAILY) |
| page_no | X | 페이지 번호 |
| num_of_rows | X | 페이지 크기 |

#### water_info (국립환경과학원 수질 DB)
| 파라미터 | 필수 | 설명 |
|----------|------|------|
| year | O | 측정연도 (예: "2024") |
| pt_no | X | 측정지점 코드 |
| page_no | X | 페이지 번호 |
| num_of_rows | X | 페이지 크기 |

**응답 (200)**:
```json
{
  "connector_key": "keco_air",
  "snapshot_id": "...",
  "status": "success",
  "evidence_count": 12,
  "error_message": null
}
```

**에러 응답**:
```json
{
  "connector_key": "keco_air",
  "snapshot_id": "...",
  "status": "error",
  "evidence_count": 0,
  "error_message": "DATA_GO_KR_API_KEY 환경변수가 설정되지 않았습니다."
}
```

---

## 유사사례 (Similar Cases)

### POST /similar-cases

유사사례를 등록합니다.

**요청**:
```json
{
  "name": "○○ 고속도로 건설사업 환경영향평가",
  "project_type": "road",
  "location": { "type": "Point", "coordinates": [127.0, 37.5] },
  "area_sqm": 500000.0,
  "completed_at": "2023-06-15T00:00:00+09:00",
  "summary": "서울~수원 구간 고속도로 환경영향평가",
  "key_findings": {
    "air_quality": "PM10 연평균 기준치 이내",
    "noise_vibration": "방음벽 설치 필요"
  },
  "evidence_categories": ["air_quality", "water_quality", "noise_vibration"],
  "source_url": "https://example.com/report"
}
```

**응답 (201)**: SimilarCaseRead 객체

### GET /similar-cases

유사사례 목록을 조회합니다.

**쿼리 파라미터**:
| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| project_type | string | X | 사업유형 필터 |
| skip | int | X | 페이지네이션 |
| limit | int | X | 페이지네이션 |

**응답 (200)**: `{ "items": [...], "total": N }`

### GET /similar-cases/{case_id}

**응답 (200)**: SimilarCaseRead 객체

### PATCH /similar-cases/{case_id}

**요청**: 변경할 필드만 전송
**응답 (200)**: 수정된 SimilarCaseRead 객체

### DELETE /similar-cases/{case_id}

**응답 (204)**: 본문 없음

### GET /similar-cases/match/{project_id}

프로젝트에 대한 유사사례 매칭을 실행합니다.

**쿼리 파라미터**:
| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| top_k | int (1-50) | 10 | 반환할 최대 사례 수 |
| min_score | float (0.0-1.0) | 0.0 | 최소 유사도 점수 |

**응답 (200)**:
```json
{
  "project_id": "...",
  "matches": [
    {
      "similar_case": { "id": "...", "name": "...", ... },
      "overall_score": 0.82,
      "type_score": 1.0,
      "location_score": 0.65,
      "scale_score": 0.78,
      "category_score": 0.85
    }
  ],
  "total": 1
}
```

---

## 섹션 (Sections)

### GET /projects/{project_id}/sections/definitions

EIA 11개 섹션 정의를 반환합니다 (DB 비의존).

**응답 (200)**:
```json
[
  {
    "key": "air_quality",
    "title": "대기질",
    "description": "대기오염물질 현황 및 영향 예측",
    "evidence_category": "air_quality",
    "required_indicators": ["PM10_연평균", "PM2.5_연평균", "NO2_연평균", "SO2_연평균", "CO_연평균", "O3_연평균"],
    "order": 1
  },
  ...
]
```

### GET /projects/{project_id}/sections/status

전체 섹션의 증거 충족 상태를 반환합니다.

**응답 (200)**:
```json
{
  "project_id": "...",
  "sections": [
    {
      "section_key": "air_quality",
      "title": "대기질",
      "description": "대기오염물질 현황 및 영향 예측",
      "order": 1,
      "total_evidence_count": 12,
      "required_indicators": [
        { "name": "PM10_연평균", "fulfilled": true, "evidence_count": 3 },
        { "name": "PM2.5_연평균", "fulfilled": true, "evidence_count": 2 },
        { "name": "NO2_연평균", "fulfilled": false, "evidence_count": 0 }
      ],
      "fulfilled_count": 4,
      "required_count": 6,
      "coverage_ratio": 0.6667,
      "status": "partial"
    }
  ],
  "total_sections": 11
}
```

### GET /projects/{project_id}/sections/status/{section_key}

단일 섹션의 충족 상태를 반환합니다.

**응답 (200)**: SectionStatusRead 객체
**응답 (404)**: `{ "detail": "섹션을 찾을 수 없습니다: {section_key}" }`

### GET /projects/{project_id}/sections/scaffold

전체 초안 뼈대를 생성합니다.

**응답 (200)**:
```json
{
  "project_id": "...",
  "generated_at": "2026-03-12T10:00:00+00:00",
  "sections": [
    {
      "section_key": "air_quality",
      "title": "대기질",
      "description": "...",
      "order": 1,
      "evidence_entries": [
        {
          "evidence_id": "...",
          "indicator": "PM10_연평균",
          "value": "42",
          "numeric_value": 42.0,
          "unit": "ug/m3",
          "observed_at": "2024-01-15T00:00:00+09:00",
          "data_source_id": "...",
          "metadata_json": {}
        }
      ],
      "summary_text": "[대기질] 현황 근거 데이터 (12건)\n\n■ PM10_연평균\n  - 측정값: 42 ug/m3 (관측: 2024-01-15)\n..."
    }
  ],
  "total_evidence_count": 24
}
```

### GET /projects/{project_id}/sections/scaffold/{section_key}

단일 섹션의 초안 뼈대를 생성합니다.

**응답 (200)**: ScaffoldSectionRead 객체
**응답 (404)**: `{ "detail": "섹션을 찾을 수 없습니다: {section_key}" }`

---

## QA

### GET /projects/{project_id}/qa

QA 규칙을 실행하고 결과를 반환합니다.

**응답 (200)**:
```json
{
  "project_id": "...",
  "run_at": "2026-03-12T10:00:00+00:00",
  "issues": [
    {
      "rule_id": "R001",
      "severity": "critical",
      "section_key": "water_quality",
      "title": "수질 섹션 증거 없음",
      "message": "수질 섹션에 대한 증거 데이터가 전혀 수집되지 않았습니다.",
      "indicators": ["BOD", "COD", "SS", "T-N", "T-P", "DO"]
    },
    {
      "rule_id": "R002",
      "severity": "critical",
      "section_key": "air_quality",
      "title": "대기질 필수 지표 누락 (2건)",
      "message": "대기질 섹션의 필수 지표 중 2건이 누락되었습니다: NO2_연평균, SO2_연평균",
      "indicators": ["NO2_연평균", "SO2_연평균"]
    },
    {
      "rule_id": "R005",
      "severity": "info",
      "section_key": "air_quality",
      "title": "대기질 — PM10_연평균 근거 1건",
      "message": "PM10_연평균 지표에 대한 근거가 1건뿐입니다. 신뢰도 향상을 위해 추가 데이터 수집을 고려하세요.",
      "indicators": ["PM10_연평균"]
    }
  ],
  "summary": {
    "critical_count": 2,
    "warning_count": 0,
    "info_count": 1,
    "total": 3
  },
  "export_ready": false
}
```

### GET /projects/{project_id}/qa/export-ready

Export 가능 여부만 빠르게 확인합니다.

**응답 (200)**:
```json
{
  "project_id": "...",
  "export_ready": false,
  "critical_count": 2,
  "message": "2건의 critical 이슈가 있어 export가 차단되었습니다."
}
```

Export 가능한 경우:
```json
{
  "project_id": "...",
  "export_ready": true,
  "critical_count": 0,
  "message": "export 가능합니다."
}
```

---

## Export

### POST /projects/{project_id}/export/docx

DOCX 파일을 생성하여 다운로드합니다.

**응답 (200)**: DOCX 파일 스트리밍
- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Content-Disposition: `attachment; filename="EIA_{name}_{timestamp}.docx"`

**응답 (400)**: Export Gate 차단
```json
{
  "detail": "critical QA 이슈가 N건 존재하여 export할 수 없습니다. QA 결과를 먼저 확인하세요."
}
```

**응답 (404)**: 프로젝트를 찾을 수 없음

---

## 공통 에러 응답

### 400 Bad Request
잘못된 요청 파라미터 또는 비즈니스 규칙 위반.
```json
{ "detail": "에러 메시지" }
```

### 404 Not Found
요청한 리소스를 찾을 수 없음.
```json
{ "detail": "리소스 not found" }
```

### 422 Unprocessable Entity
요청 본문 유효성 검사 실패 (Pydantic 검증).
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
서버 내부 오류.
```json
{ "detail": "Internal server error" }
```
