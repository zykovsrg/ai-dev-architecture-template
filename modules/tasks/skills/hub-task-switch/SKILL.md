---
name: hub-task-switch
description: Change one confirmed registered project's unfinished task and report the change.
---

# Hub Task Switch

Use this skill only after explicit confirmation of a confirmed registered
project and after the hub-owned `hub-task-intake` classifies the request as a
different task. Its scope is the selected project `ai/` memory only; do not
require or read duplicated project `AGENTS.md` or `CLAUDE.md` files.

Module rules: `ai/rules/tasks.md`.

## Procedure

1. Read only the selected project's `ai/current-task.md` and
   `ai/paused-tasks.md`.
2. Pause the current task, write the replacement task, or promote a future
   task directly, then report the old goal, the new goal, and the changed
   files.
3. Make only the requested memory changes in the selected project. Never transfer task content to another project. Keep the paused
   task's existing immutable `Task ID:` when moving it into
   `ai/paused-tasks.md`. Give the replacement task
   a concrete immutable `Task ID:` in the
   `TASK-<project-id>-<UTC-date>-<NNN>` form, where `<NNN>` is the next free
   three-digit number for that date in the selected project; never leave a
   placeholder. A promoted future task keeps exactly the same immutable ID
   when it becomes current.
4. After a write to the selected project's task files, run the
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
memory-isolation rules. It never changes task state during a project switch.
