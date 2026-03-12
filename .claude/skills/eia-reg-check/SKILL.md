---
name: eia-reg-check
description: Apply the MVP legal-structure rules for the 환경영향평가서 초안 and compute mandatory section status.
user-invocable: false
allowed-tools: Read, Grep, Glob
---

Use this skill whenever work touches:
- section planning
- mandatory fields
- draft status computation
- legal completeness
- any argument about whether an item can be auto-filled

Checklist:
1. Confirm the task is still within the MVP document type: `환경영향평가서 초안`.
2. Read `docs/claude/phase-plan.md` for section definitions and design principles.
3. Map requested behavior to one of the approved section states.
4. Reject designs that imply full autonomous completion for expert-only sections.
5. If an item depends on public procedure or expert judgment, mark it accordingly instead of fabricating text.

Output style:
- mention the affected section(s)
- list the computed state(s)
- note any missing required fields
- identify whether human review is mandatory
