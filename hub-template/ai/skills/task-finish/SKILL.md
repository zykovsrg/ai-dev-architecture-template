---
name: task-finish
description: Verify and close one confirmed registered project's task memory after separate approval.
---

# Hub Task Finish

Use this skill only after explicit confirmation of a confirmed registered
project and when the user asks to close its task. Its scope is the selected
project `ai/` memory only; do not require or read duplicated project
`AGENTS.md` or `CLAUDE.md` files.

## Procedure

1. Read the selected project's `ai/current-task.md` and the smallest relevant
   `ai/decisions.md`, `ai/changelog.md`, or `ai/future-tasks.md` file.
2. Check recorded Done criteria and report any missing verification or open
   risk. Do not change task memory during this check.
3. Require a separate explicit confirmation before writing the approved
   changelog, decision, future-task, or current-task cleanup.
4. After confirmation, save only the selected project's result through its
   repository and report whether it was saved locally or pushed.

This workflow cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules. It never closes, copies, or cleans another project's
task memory.
