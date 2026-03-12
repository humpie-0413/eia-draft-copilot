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
