# Output Contracts

## Section states
| State | Meaning | Can export as final section? |
|---|---|---|
| AUTO_FILLED | Structured inputs and public data are enough to fill the item | Yes, after QA |
| EVIDENCE_DRAFT | Evidence exists, but text or interpretation still needs review | Usually no |
| EXPERT_REQUIRED | Expert judgment is required to complete or approve the item | No |
| PROCEDURE_PENDING | External process or procedural step is not yet complete | No |
| NOT_APPLICABLE | The item does not apply to this project | Yes |

## Evidence item contract
```json
{
  "id": "uuid",
  "projectId": "uuid",
  "medium": "ecology|landuse|air|noise|hydrology|geology|procedure|other",
  "title": "string",
  "normalizedValue": {},
  "sourceSnapshotId": "uuid",
  "observedAt": "ISO-8601 or null",
  "spatialRelation": "inside|intersects|nearby|regional|unknown",
  "isScreeningOnly": false,
  "confidence": 1.0
}
```

## Draft claim contract
```json
{
  "claim": "string",
  "evidenceIds": ["uuid-1", "uuid-2"],
  "confidence": 0.0,
  "requiresExpertReview": false,
  "unresolvedQuestions": []
}
```

## Section draft contract
```json
{
  "sectionCode": "string",
  "sectionTitle": "string",
  "state": "AUTO_FILLED",
  "bodyMarkdown": "string",
  "claims": [],
  "missingFields": [],
  "unresolvedQuestions": [],
  "notes": []
}
```

## QA issue contract
```json
{
  "id": "uuid",
  "projectId": "uuid",
  "sectionCode": "string",
  "severity": "critical|high|medium|low",
  "ruleCode": "string",
  "message": "string",
  "suggestedFix": "string",
  "status": "open|resolved"
}
```

## Export gate
- export is blocked if any `critical` issue is open
- appendices are optional unless explicitly requested by the export job
- unsupported claims must never be silently dropped

---

## 구현 현황 (Post-0.5 기준)

### Section states
| 스펙 상태 | 구현 상태 | 비고 |
|-----------|-----------|------|
| AUTO_FILLED | ✅ `auto_filled` | complete + 모든 evidence에 snapshot_id 있을 때 판정 |
| EVIDENCE_DRAFT | ✅ enum 정의 완료 | 판정 로직은 Post-3(초안 텍스트 생성기)에서 구현 예정 |
| EXPERT_REQUIRED | ✅ enum 정의 완료 | 판정 로직은 향후 플래그 기반으로 구현 예정 |
| PROCEDURE_PENDING | ❌ 미구현 | MVP 범위 외 (외부 절차 연동 필요) |
| NOT_APPLICABLE | ✅ enum 정의 완료 | 사용자 수동 설정 기능은 향후 구현 예정 |
| *(추가)* empty | ✅ | 증거 0건 — 기본 충족도 기반 상태 |
| *(추가)* partial | ✅ | 일부 지표 충족 — 기본 충족도 기반 상태 |
| *(추가)* complete | ✅ | 전체 지표 충족 — 기본 충족도 기반 상태 |

### Evidence item contract
| 스펙 필드 | 구현 필드 | 상태 |
|-----------|-----------|------|
| id | id | ✅ |
| projectId | project_id | ✅ (snake_case) |
| medium | category + 매핑 함수 | ✅ `category_to_medium()` / `medium_to_category()` 추가 |
| title | *(없음)* | ❌ 미구현 — indicator + value로 대체 |
| normalizedValue | *(없음)* | ❌ 미구현 — value + numeric_value로 분리 저장 |
| sourceSnapshotId | snapshot_id | ✅ |
| observedAt | observed_at | ✅ |
| spatialRelation | *(없음)* | ❌ 미구현 — 현재 작동에 영향 없음 |
| isScreeningOnly | screening_only | ✅ |
| confidence | *(없음)* | ❌ 미구현 — 현재 작동에 영향 없음 |

### Draft claim contract
- ❌ **전체 미구현** — Post-6(LLM 연동)에서 구현 예정

### Section draft contract
| 스펙 필드 | 구현 필드 | 상태 |
|-----------|-----------|------|
| sectionCode | section_key | ✅ |
| sectionTitle | title | ✅ |
| state | state | ✅ Post-0.5에서 추가 |
| bodyMarkdown | summary_text | ✅ (plain text, markdown 전환은 Post-3) |
| claims | *(없음)* | ❌ Post-6(LLM 연동)에서 구현 예정 |
| missingFields | missing_indicators | ✅ Post-0.5에서 추가 |
| unresolvedQuestions | *(없음)* | ❌ Post-6에서 구현 예정 |
| notes | *(없음)* | ❌ 향후 구현 예정 |

### QA issue contract
| 스펙 필드 | 구현 필드 | 상태 | 비고 |
|-----------|-----------|------|------|
| id | *(없음)* | ❌ | QA 이슈는 매번 재계산, 별도 ID 불필요 |
| projectId | QaResult.project_id | ✅ | 결과 수준에서 제공 |
| sectionCode | section_key | ✅ | |
| severity | severity | ⚠️ 값 체계 다름 | 스펙: critical/high/medium/low → 구현: critical/warning/info |
| ruleCode | rule_id | ✅ | |
| message | message | ✅ | |
| suggestedFix | *(없음)* | ❌ | 향후 추가 예정 |
| status | *(없음)* | ❌ | 매번 재계산 방식, 상태 저장 불필요 |

### Export gate
- ✅ critical 이슈 시 export 차단
- ✅ unsupported claim 검출 (R004)
- ✅ DOCX/PDF 출력
