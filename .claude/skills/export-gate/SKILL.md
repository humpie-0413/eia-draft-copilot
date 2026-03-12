---
name: export-gate
description: Manually verify export readiness and block document output if critical QA issues remain.
disable-model-invocation: true
argument-hint: [project-id-or-export-target]
allowed-tools: Read, Grep, Glob, Bash
---

Run the export readiness check for `$ARGUMENTS`.

Procedure:
1. Read current QA issues.
2. Count issues by severity.
3. Block export if any `critical` issues are open.
4. Confirm required appendices are available when requested.
5. Emit a short export decision summary.

Output:
- export allowed: yes/no
- blocking issues
- missing appendices
- next action
