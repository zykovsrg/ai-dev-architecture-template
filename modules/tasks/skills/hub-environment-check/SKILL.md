---
name: hub-environment-check
description: Check one confirmed registered project's AI task state through the hub-managed flow.
---

# Hub Environment Check

Use this skill only after explicit confirmation of a confirmed registered
project and successful hub registry validation. Its scope is the selected
project `ai/` memory only; do not require or read duplicated project
`AGENTS.md` or `CLAUDE.md` files.

Module rules: `ai/rules/tasks.md`.

## Procedure

1. Restate the confirmed project ID and canonical registered path.
2. Validate that the exact memory path and its components remain inside the
   confirmed project and are not symlinks before reading. Read `ai/current-task.md` and, only when needed to explain an unfinished
   task, `ai/paused-tasks.md` inside that project.
3. If current-task memory is missing or invalid, report adaptation needed and
   use the readiness procedure in `hub-project-register` for the already
   confirmed registered project. Do not infer an empty task from missing data.
4. Report whether task memory is available, the recorded status/stage, and
   whether `hub-task-intake`, `hub-task-switch`, or `hub-task-finish` is the next hub-owned
   workflow. Do not change memory during this check.

This workflow cannot override hub routing, allowed roots, secret, or
memory-isolation rules. It never reads another project's files or secret data.
