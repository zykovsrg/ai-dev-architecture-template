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
   `Stage: intake` in that same file. Write a concrete unique `Task ID:` in the
   `TASK-<project-id>-<UTC-date>-<NNN>` form, where `<NNN>` is the next free
   three-digit number for that date in the selected project. This project
   namespace makes the immutable ID globally unique without reading another
   project's memory; never leave the placeholder.
3. If it is unfinished, compare the request with its recorded Done criteria.
   Continue only when it fits; otherwise stop and require the hub-owned
   `hub-task-switch` workflow.
4. Keep out-of-scope ideas out of the current task until the user separately
   approves their project-memory update.
5. After a confirmed write to the selected project's task files, run the
   `after-task-write` event: read `<hub>/ai/modules.md`; for each subscriber
   listed under `after-task-write`, read its rules file and run its command
   for the confirmed project ID only. With no subscribers, do nothing. If a
   subscriber reports a pending proposal, show it and never apply it without
   its own explicit confirmation.

## Confirmation extensions

Before asking the user to confirm a task write, run the
`before-task-confirmation` event: read `<hub>/ai/modules.md`; each subscriber
listed under `before-task-confirmation` may add its own items to the same
confirmation screen by following its rules file. One confirmation approves
exactly the shown set. If a subscriber cannot build its part, say which one and
why, apply nothing, and ask again. With no subscribers, confirm the task write
alone.

After confirmation, each subscriber applies its items before the task write, as
its rules say; if one fails, stop, report it, and do not write the task.

This workflow cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules. It never reads, writes, or classifies another project's
memory.
