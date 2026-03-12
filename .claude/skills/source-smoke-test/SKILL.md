---
name: source-smoke-test
description: Run a lightweight validation pass on public-data connectors, response formats, CRS assumptions, and empty-result handling.
disable-model-invocation: true
argument-hint: [source-name-or-endpoint]
allowed-tools: Read, Write, Edit, MultiEdit, Grep, Glob, Bash
---

Smoke-test the source or connector specified in `$ARGUMENTS`.

Steps:
1. Identify the connector code and its output contract.
2. Verify expected format handling:
   - XML / JSON / file download / WMS / WFS
3. Check coordinate handling and CRS assumptions.
4. Inspect empty-result handling and retry behavior.
5. Record findings in `docs/progress/WORKLOG.md` if changes are made.

Return:
- connector touched
- test command used
- pass/fail findings
- follow-up fixes required
