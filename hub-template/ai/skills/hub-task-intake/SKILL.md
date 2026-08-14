---
name: hub-task-intake
description: Record or classify requested work for one confirmed registered project without crossing hub boundaries.
---

# Hub Task Intake

Use this skill only after explicit confirmation of a confirmed registered
project and after the hub-owned `hub-environment-check`. Its scope is the selected
project `ai/` memory only; do not require or read duplicated project
`AGENTS.md` or `CLAUDE.md` files.

## Procedure

1. Read the selected project's `ai/current-task.md`.
2. If it is empty, record the user's requested goal, scope, Done criteria, and
   `Stage: intake` in that same file.
3. If it is unfinished, compare the request with its recorded Done criteria.
   Continue only when it fits; otherwise stop and require the hub-owned
   `hub-task-switch` workflow.
4. Keep out-of-scope ideas out of the current task until the user separately
   approves their project-memory update.

This workflow cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules. It never reads, writes, or classifies another project's
memory.
