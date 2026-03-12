---
name: ui-assembly-shadcn
description: Build or refactor screens using shadcn/ui patterns, CLI, skills, and MCP-aware workflows.
user-invocable: false
allowed-tools: Read, Write, Edit, MultiEdit, Grep, Glob, Bash
---

Use this skill for any UI implementation work.

Process:
1. Inspect existing `components.json` and installed components.
2. Prefer shadcn CLI or shadcn MCP to add missing primitives.
3. Build with composable patterns:
   - form
   - table
   - tabs
   - sheet
   - dialog
   - badge
   - card
4. Keep the screen aligned with internal-tool UX.
5. Avoid one-off styles when an existing shadcn component can be extended.

For each UI task, report:
- components used
- components added
- whether shadcn CLI or MCP was used
- any follow-up cleanup needed
