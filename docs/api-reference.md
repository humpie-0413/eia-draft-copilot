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

**응답 (201)**: ProjectRead 객체

### GET /projects

프로젝트 목록을 조회합니다.

**쿼리 파라미터**:
| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| skip | int (≥0) | 0 | 건너뛸 항목 수 |
| limit | int (1-100) | 50 | 조회 항목 수 |

**응답 (200)**: `{ "items": [...], "total": N }`

### GET /projects/{project_id}

**응답 (200)**: ProjectRead 객체
**응답 (404)**: `{ "detail": "Project not found" }`

### PATCH /projects/{project_id}

프로젝트를 수정합니다. 변경할 필드만 전송합니다.

**응답 (200)**: 수정된 ProjectRead 객체

### DELETE /projects/{project_id}

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
  "screening_only": false
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
| screening_only | bool | X | 스크리닝 전용 여부 (기본 false) |

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
| skip | int (≥0) | X | 페이지네이션 |
| limit | int (1-100) | X | 페이지네이션 (기본 50) |

**응답 (200)**: `{ "items": [...], "total": N }`

### GET /evidences/{evidence_id}

**응답 (200)**: EvidenceRead 객체

### PATCH /evidences/{evidence_id}

**응답 (200)**: 수정된 EvidenceRead 객체

### DELETE /evidences/{evidence_id}

**응답 (204)**: 본문 없음

---

## 커넥터 (Connectors)

### GET /connectors

사용 가능한 커넥터 목록을 조회합니다 (4종).

**응답 (200)**:
```json
[
  { "connector_key": "keco_air", "display_name": "한국환경공단 대기질 (에어코리아)" },
  { "connector_key": "water_info", "display_name": "국립환경과학원 수질 DB (물환경 수질측정망)" },
  { "connector_key": "soil_info", "display_name": "국립환경과학원 토양측정망" },
  { "connector_key": "kma_weather", "display_name": "기상청 지상(ASOS) 일자료" }
]
```

### POST /connectors/{connector_key}/collect

데이터 수집을 실행합니다.

**커넥터별 파라미터**:

#### keco_air (에어코리아 대기질)
| 파라미터 | 필수 | 설명 |
|----------|------|------|
| station_name | O | 측정소명 (예: "종로구", "강남구") |
| data_term | X | 조회기간 (DAILY/MONTH/3MONTH, 기본 DAILY) |

#### water_info (국립환경과학원 수질 DB)
| 파라미터 | 필수 | 설명 |
|----------|------|------|
| year | O | 측정연도 (예: "2024") |
| pt_no | X | 측정지점 코드 |

#### soil_info (국립환경과학원 토양측정망)
| 파라미터 | 필수 | 설명 |
|----------|------|------|
| year | O | 측정연도 (예: "2023") |
| sido | X | 시도 (예: "서울특별시") |

#### kma_weather (기상청 ASOS 일자료)
| 파라미터 | 필수 | 설명 |
|----------|------|------|
| stn_id | O | 관측소 번호 (예: "108"=서울) |
| start_dt | O | 시작일 (YYYYMMDD) |
| end_dt | O | 종료일 (YYYYMMDD) |

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

---

## 유사사례 (Similar Cases)

### POST /similar-cases

유사사례를 등록합니다.

### GET /similar-cases

유사사례 목록을 조회합니다.

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
      "similar_case": { "id": "...", "name": "..." },
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

### GET /projects/{project_id}/sections/status

전체 섹션의 증거 충족 상태를 반환합니다.

### GET /projects/{project_id}/sections/scaffold

전체 초안 뼈대를 생성합니다.

**응답 필드** (Post-3 이후):
- `narrative`: 서술문 텍스트 (섹션별 자동 생성)
- `summary_text`: 통계 요약 + 환경기준 비교 + 상세 데이터
- `evidence_entries`: 증거 목록

---

## 통계 (Statistics) — Post-1

### GET /projects/{project_id}/statistics

프로젝트의 전체 섹션별 통계를 반환합니다.

**쿼리 파라미터**:
| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| years_filter | int | null | 연도 필터 (0=전체, null=기본값, N=최근 N년) |
| aggregate_daily | bool | false | 일평균 집계 여부 |

**응답 (200)**:
```json
{
  "project_id": "...",
  "generated_at": "...",
  "sections": [
    {
      "section_key": "air_quality",
      "title": "대기질",
      "total_numeric_count": 12,
      "indicator_stats": [
        {
          "indicator": "PM10_연평균",
          "count": 3,
          "mean": 42.0,
          "max_value": 48.0,
          "min_value": 38.0,
          "std_dev": 4.5,
          "unit": "ug/m3",
          "period_start": "2024-01-15",
          "period_end": "2024-12-15"
        }
      ],
      "years_filter_applied": 1
    }
  ],
  "total_numeric_count": 45
}
```

### GET /projects/{project_id}/statistics/{section_key}

특정 섹션의 통계를 반환합니다.

---

## 환경기준 비교 (Standards Check) — Post-2

### GET /projects/{project_id}/standards-check

프로젝트의 전체 섹션별 환경기준 비교 결과를 반환합니다.

**쿼리 파라미터**: 통계 API와 동일 (years_filter, aggregate_daily)

**응답 (200)**:
```json
{
  "project_id": "...",
  "generated_at": "...",
  "sections": [
    {
      "section_key": "air_quality",
      "title": "대기질",
      "indicators": [
        {
          "indicator": "PM10_연평균",
          "standard_value": 50.0,
          "standard_unit": "ug/m3",
          "time_basis": "연평균",
          "measured_avg": 42.0,
          "measured_max": 48.0,
          "measured_count": 3,
          "status": "pass",
          "exceedance_rate": 0.0,
          "description": "PM10 연평균: 42.0 ug/m3 ≤ 기준 50.0 ug/m3 → 적합"
        }
      ],
      "water_grade": null,
      "water_grade_name": null,
      "has_exceedance": false,
      "exceedance_count": 0,
      "summary": "대기질 환경기준 비교 결과..."
    }
  ],
  "total_exceedance_count": 0
}
```

### GET /projects/{project_id}/standards-check/{section_key}

특정 섹션의 환경기준 비교 결과를 반환합니다.

---

## QA

### GET /projects/{project_id}/qa

QA 규칙을 실행하고 결과를 반환합니다.

**응답 (200)**:
```json
{
  "project_id": "...",
  "run_at": "...",
  "issues": [
    {
      "rule_id": "R001",
      "severity": "critical",
      "section_key": "water_quality",
      "title": "수질 섹션 증거 없음",
      "message": "...",
      "indicators": ["BOD", "COD", "SS", "T-N", "T-P", "DO"]
    }
  ],
  "summary": {
    "critical_count": 2,
    "warning_count": 1,
    "info_count": 1,
    "total": 4
  },
  "export_ready": false
}
```

### GET /projects/{project_id}/qa/export-ready

Export 가능 여부만 빠르게 확인합니다.

---

## Export — Post-5

### GET /projects/{project_id}/export/preview

Export 전 문서 구조 미리보기를 반환합니다.

**응답 (200)**:
```json
{
  "project_name": "...",
  "project_type": "power_plant",
  "centroid": [37.50, 127.04],
  "sections": [
    {
      "title": "대기질",
      "state": "complete",
      "evidence_count": 12,
      "has_stats": true,
      "has_standards": true
    }
  ],
  "total_evidence": 45,
  "similar_case_count": 3,
  "qa_issue_count": 5,
  "export_ready": true
}
```

### POST /projects/{project_id}/export/docx

DOCX 파일을 생성하여 다운로드합니다.

**쿼리 파라미터**:
| 이름 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| include_appendix_a | bool | true | 부록 A (상세 측정 데이터) 포함 |
| include_appendix_b | bool | true | 부록 B (유사사례 매칭) 포함 |
| include_appendix_c | bool | true | 부록 C (QA 검사 결과) 포함 |

**응답 (200)**: DOCX 파일 스트리밍
**응답 (422)**: Export Gate 차단

### GET /projects/{project_id}/export/pdf

PDF 파일을 생성하여 다운로드합니다.

**쿼리 파라미터**: DOCX와 동일

**응답 (200)**: PDF 파일 스트리밍
**응답 (422)**: Export Gate 차단

---

## LLM — Post-6

### GET /llm/status

현재 LLM adapter 설정 및 API 키 상태를 반환합니다.

**응답 (200)**:
```json
{
  "adapter": "none",
  "available": true,
  "openai_key_set": false,
  "google_key_set": false
}
```

### POST /llm/projects/{project_id}/enhance

특정 섹션의 서술문을 LLM으로 보강합니다.

**요청**:
```json
{
  "section_key": "air_quality"
}
```

**응답 (200)**:
```json
{
  "section_key": "air_quality",
  "original_narrative": "대기질 현황을 분석한 결과...",
  "enhanced_narrative": "본 사업 부지 주변의 대기질 현황을 분석한 결과...",
  "adapter_used": "openai_paid",
  "is_fallback": false
}
```

---

## 공통 에러 응답

### 400 Bad Request
```json
{ "detail": "에러 메시지" }
```

### 404 Not Found
```json
{ "detail": "리소스 not found" }
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    { "loc": ["body", "name"], "msg": "field required", "type": "value_error.missing" }
  ]
}
```

### 500 Internal Server Error
```json
{ "detail": "Internal server error" }
```
