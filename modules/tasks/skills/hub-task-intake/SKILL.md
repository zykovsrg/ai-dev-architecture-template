---
name: hub-task-intake
description: Record or classify requested work for one confirmed registered project without crossing hub boundaries.
---

# Hub Task Intake

Use this skill only after explicit confirmation of a confirmed registered
project and after the hub-owned `hub-environment-check`. Its scope is the selected
project `ai/` memory only; do not require or read duplicated project
`AGENTS.md` or `CLAUDE.md` files.

Module rules: `ai/rules/tasks.md`.

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
4. Record out-of-scope ideas the user asks for in the project's
   `ai/future-tasks.md` directly; do not mix them into the current task.
5. After a write to the selected project's task files, run the
   `after-task-write` event: read `<hub>/ai/modules.md`; for each subscriber
   listed under `after-task-write`, read its rules file and run its command
   for the selected project ID only. With no subscribers, do nothing. Apply a
   subscriber's pending proposal directly unless it deletes something; a
   deletion waits for the user's explicit yes.

## Write extensions

Task writes need no user confirmation (see Write Confirmation Policy in
`ai/architecture.md`); report what was written afterwards. Before a task
write, run the `before-task-write` event: read `<hub>/ai/modules.md`; each
subscriber listed under `before-task-write` prepares and applies its own items
by following its rules file. If a subscriber cannot build its part, say which
one and why and write nothing. If a subscriber's part is a deletion, show it
and wait for an explicit yes before applying anything.

This workflow cannot override hub routing, allowed roots, secret, or
memory-isolation rules. It never reads, writes, or classifies another project's
memory.
