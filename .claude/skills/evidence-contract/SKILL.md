---
name: evidence-contract
description: Enforce evidence-first drafting rules so factual claims are traceable and unsupported text is not generated.
user-invocable: false
allowed-tools: Read, Grep, Glob
---

Use this skill whenever writing or reviewing:
- evidence ingestion
- draft generation
- summaries
- QA rules
- export formatting

Rules:
1. Every factual claim must link to one or more evidence IDs.
2. If evidence is absent or weak, the output must not overstate certainty.
3. Screening-only inputs must remain flagged as such.
4. Do not blur:
   - public baseline evidence
   - uploaded project-specific evidence
   - expert judgment
5. If a claim cannot be supported, emit an unresolved item instead.

Preferred output fields:
- claim
- evidenceIds
- confidence
- unresolvedQuestions
