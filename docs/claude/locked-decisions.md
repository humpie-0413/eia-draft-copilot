# Locked Decisions

## Product identity
- Product name: `EIA Draft Copilot`
- Positioning: internal B2B drafting and QA software for registered Korean EIA firms
- Not a full autonomous report writer
- Not an outsourcing/evaluation agency

## MVP document scope
- Exactly one document type: `환경영향평가서 초안`
- Do not expand to 전략환경영향평가, 소규모환경영향평가, 사후환경영향조사 in MVP
- Do not expand to local ordinance variants in MVP

## MVP functional scope
1. project intake
2. project geometry input
3. evidence ingestion and normalization
4. similar case matching
5. section planning
6. draft scaffold / evidence-backed text
7. QA
8. DOCX/PDF export

## MVP non-goals
- final submission-ready report automation
- real-time collaboration
- tenant-based auth
- billing
- customer-facing marketing site
- fully automated expert judgment
- direct replacement of environmental consultants

## Section state model
- `AUTO_FILLED`
- `EVIDENCE_DRAFT`
- `EXPERT_REQUIRED`
- `PROCEDURE_PENDING`
- `NOT_APPLICABLE`

## LLM policy
- MVP must work with `LLM_MODE=none`
- `manual_prompt_pack` is allowed in MVP
- `gemini_free` is optional enhancement
- paid models are phase-2 upgrades, not MVP dependencies

## Data policy
- Store raw source snapshots
- Normalize evidence separately
- Geometry storage CRS: EPSG:4326
- Screening-only evidence must remain flagged
- Every factual claim requires evidence IDs

## UI policy
- shadcn/ui only
- internal operations style, not a consumer app
- dense tables, forms, cards, badges, dialogs, sheets
- map UI is supportive, not the primary value surface

## Quality gates
- no unsupported factual claims
- no export when `critical` QA issues are open
- no schema changes without migration
- no hidden redesigns without explicit human approval

## Change policy
Treat everything above as frozen unless the human explicitly requests a pivot.
