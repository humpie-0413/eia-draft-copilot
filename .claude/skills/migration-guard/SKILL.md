---
name: migration-guard
description: Ensure database model changes are mirrored by Alembic migrations and schema impacts are documented.
user-invocable: false
allowed-tools: Read, Grep, Glob, Bash
---

Use this skill whenever files under `backend/app/models/`, `backend/app/schemas/`, or repository layers are changed.

Checks:
1. Did the SQLAlchemy model change?
2. Is an Alembic migration present or intentionally unnecessary?
3. Did request/response schemas change?
4. Do tests or fixtures need updating?
5. Are UUIDs, timestamps, and foreign keys consistent with project conventions?

If migration drift is detected, call it out explicitly.
