---
name: environment-check
description: Check one confirmed registered project's AI task state through the hub-managed flow.
---

# Hub Environment Check

Use this skill only after explicit confirmation of a confirmed registered
project and successful hub registry validation. Its scope is the selected
project `ai/` memory only; do not require or read duplicated project
`AGENTS.md` or `CLAUDE.md` files.

## Procedure

1. Restate the confirmed project ID and canonical registered path.
2. Read `ai/current-task.md` and, only when needed to explain an unfinished
   task, `ai/paused-tasks.md` inside that project.
3. Report whether task memory is available, the recorded status/stage, and
   whether `task-intake`, `task-switch`, or `task-finish` is the next hub-owned
   workflow. Do not change memory during this check.

This workflow cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules. It never reads another project's files or secret data.
