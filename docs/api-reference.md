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

사용 가능한 커넥터 목록을 조회합니다 (8종 정의, 4종 운영 중).

**응답 (200)**:
```json
[
  { "connector_key": "keco_air", "display_name": "한국환경공단 대기질 (에어코리아)" },
  { "connector_key": "water_info", "display_name": "국립환경과학원 수질 DB (물환경 수질측정망)" },
  { "connector_key": "soil_info", "display_name": "국립환경과학원 토양측정망" },
  { "connector_key": "kma_weather", "display_name": "기상청 지상(ASOS) 일자료" },
  { "connector_key": "vworld_land_use", "display_name": "V-world 토지이용 (2D데이터)" },
  { "connector_key": "cultural_heritage", "display_name": "국가유산청 문화재 조회" },
  { "connector_key": "traffic_volume", "display_name": "한국건설기술연구원 교통량 통계 (KICT)" },
  { "connector_key": "waste_stats", "display_name": "행정안전부 생활쓰레기배출정보" }
]
```

**커넥터 가용 현황**:
| 커넥터 | 상태 | 비고 |
|--------|------|------|
| `keco_air` | ✅ 운영 중 | 공공데이터포털 API 키 필요 |
| `water_info` | ✅ 운영 중 | 공공데이터포털 API 키 필요 |
| `cultural_heritage` | ✅ 운영 중 | API 키 불필요 (공개 API) |
| `waste_stats` | ✅ 운영 중 | 공공데이터포털 API 키 필요. 배출 일정/관리 정보 수집 (발생량 아님) |
| `soil_info` | ⚠️ 일시 불가 | API 서버 오류 (500) |
| `kma_weather` | ⚠️ 일시 불가 | API 키 승인 대기 |
| `vworld_land_use` | ⚠️ 일시 불가 | VWORLD_API_KEY 미설정 |
| `traffic_volume` | ⚠️ 일시 불가 | API 엔드포인트 폐지 |

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

#### vworld_land_use (V-world 토지이용)
| 파라미터 | 필수 | 설명 |
|----------|------|------|
| lng | O | 경도 (예: "126.978") |
| lat | O | 위도 (예: "37.566") |

> `VWORLD_API_KEY` 환경변수 설정 필요

#### cultural_heritage (국가유산청 문화재)
| 파라미터 | 필수 | 설명 |
|----------|------|------|
| lng | O | 경도 (예: "126.978") |
| lat | O | 위도 (예: "37.566") |
| ccba_ctcd | X | 시도코드 (미입력 시 좌표에서 추론) |

> API 키 불필요 (공개 API). 반경 1km 이내 문화재 자동 필터링.

#### traffic_volume (교통량 통계)
| 파라미터 | 필수 | 설명 |
|----------|------|------|
| year | O | 조회 연도 (예: "2024") |
| dtype | X | 도로유형 코드 (1=고속도로, 2=일반국도, 3=지방도, 기본: 2) |
| month | X | 조회 월 (기본: 1) |

#### waste_stats (폐기물 배출정보)
| 파라미터 | 필수 | 설명 |
|----------|------|------|
| region | O | 시군구명 (예: "강남구") |
| start_date | X | 기준일 시작 (YYYYMMDD) |
| end_date | X | 기준일 종료 (YYYYMMDD) |

> 폐기물 커넥터는 폐기물 발생량이 아닌 배출 일정/관리 정보(배출요일, 배출방법, 관리부서 등)를 수집합니다.

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

## 평가 범위 (Assessment Scope) — Reg-4

### GET /projects/{project_id}/assessment-scope

프로젝트의 사업유형 기반 평가 범위를 반환합니다.
사업유형 미설정 시 'other' 기준으로 산정합니다.

**응답 (200)**:
```json
{
  "project_type": "power_plant",
  "type_name": "발전소",
  "legal_basis": "환경영향평가법 시행령 별표 3 제1호 나목",
  "sections": [
    {
      "section_key": "air_quality",
      "title": "대기질",
      "scope": "required",
      "required_indicators": ["PM10_연평균", "PM2.5_연평균", "NO2_연평균", "SO2_연평균", "CO_연평균", "O3_연평균"],
      "legal_basis": "환경영향평가법 시행령 별표 3 제1호 나목"
    },
    {
      "section_key": "climate",
      "title": "기후",
      "scope": "recommended",
      "required_indicators": [],
      "legal_basis": ""
    },
    {
      "section_key": "waste",
      "title": "폐기물",
      "scope": "optional",
      "required_indicators": [],
      "legal_basis": ""
    }
  ],
  "required_count": 5,
  "recommended_count": 2,
  "optional_count": 4
}
```

| 필드 | 설명 |
|------|------|
| scope | `required` = 법적 필수, `recommended` = 권장, `optional` = 선택 |
| required_indicators | 해당 섹션에서 법적으로 요구되는 지표 목록 (required만 해당) |
| legal_basis | 법적 근거 (필수 섹션만 해당) |

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
          "description": "PM10 연평균: 42.0 ug/m3 ≤ 기준 50.0 ug/m3 → 적합",
          "legal_basis": "환경정책기본법 시행령 별표 제1호 (대기환경기준)"
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
      "rule_id": "R007",
      "severity": "critical",
      "section_key": "water_quality",
      "title": "수질 법적 필수 섹션 누락",
      "message": "발전소 사업은 환경영향평가법 시행령 별표 3에 따라 수질 평가가 필수입니다.",
      "indicators": ["BOD", "COD", "SS", "T-N", "T-P", "DO"],
      "legal_basis": "환경영향평가법 시행령 별표 3 제1호 나목"
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

## 영향 예측 (Predictions) — Pred-1~3

### GET /prediction-models

등록된 예측 모델 목록과 입력 파라미터를 반환합니다.

**응답 (200)**:
```json
[
  {
    "name": "gaussian_plume",
    "display_name": "가우시안 플룸 대기 확산 모델",
    "description": "Pasquill-Gifford 확산계수 기반 지표면 농도 예측",
    "applicable_sections": ["air_quality"],
    "required_inputs": [
      { "name": "emission_rate_pm10", "display_name": "PM10 배출량", "unit": "g/s", "default": null, "required": false, "description": "미입력 시 사업유형별 기본값" },
      { "name": "stack_height", "display_name": "굴뚝 높이", "unit": "m", "default": null, "required": false, "description": "미입력 시 사업유형별 기본값" },
      { "name": "wind_speed", "display_name": "풍속", "unit": "m/s", "default": 3.0, "required": false, "description": "미입력 시 기상 데이터에서 자동 추출" },
      { "name": "stability_class", "display_name": "대기안정도", "unit": "", "default": "D", "required": false, "description": "Pasquill 안정도 등급 (A~F)" }
    ]
  },
  {
    "name": "noise_propagation",
    "display_name": "소음 전파 모델",
    "description": "점/선음원 거리감쇠 + Maekawa 차음벽 회절감쇠",
    "applicable_sections": ["noise_vibration"],
    "required_inputs": [...]
  },
  {
    "name": "water_mixing",
    "display_name": "수질 완전혼합 모델",
    "description": "하천 방류 시 완전혼합 희석 모델",
    "applicable_sections": ["water_quality"],
    "required_inputs": [...]
  }
]
```

### POST /projects/{project_id}/predict/{section_key}

특정 섹션의 영향 예측을 실행합니다.

**요청**:
```json
{
  "model_name": null,
  "parameters": {},
  "use_background_data": true
}
```

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| model_name | string | null | 예측 모델 이름 (null이면 섹션 기본 모델) |
| parameters | dict | {} | 입력 파라미터 (미지정 시 사업유형별 기본값) |
| use_background_data | bool | true | 배경 데이터를 evidence에서 자동 추출 |

**응답 (200)**:
```json
{
  "section_key": "air_quality",
  "model_name": "gaussian_plume",
  "input_parameters": {
    "project_type": "power_plant",
    "emission_rate_pm10": 0.5,
    "stack_height": 30.0,
    "wind_speed": 2.3,
    "stability_class": "D"
  },
  "predictions": [
    {
      "label": "100m",
      "distance_m": 100.0,
      "pollutant": "PM10",
      "predicted_concentration": 2.34,
      "background_concentration": 42.0,
      "total_concentration": 44.34,
      "unit": "ug/m3",
      "standard_value": 50.0,
      "exceeds_standard": false
    }
  ],
  "summary": "가우시안 플룸 모델 예측 결과...",
  "assumptions": ["대기안정도 D등급 (중립)...", "지형 효과 미반영..."],
  "limitations": ["간이 모델로서 정밀 모사에 한계...", "단일 점원만 고려..."]
}
```

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
