---
name: hub-task-switch
description: Safely change one confirmed registered project's unfinished task after separate approval.
---

# Hub Task Switch

Use this skill only after explicit confirmation of a confirmed registered
project and after the hub-owned `hub-task-intake` classifies the request as a
different task. Its scope is the selected project `ai/` memory only; do not
require or read duplicated project `AGENTS.md` or `CLAUDE.md` files.

## Procedure

1. Read only the selected project's `ai/current-task.md` and
   `ai/paused-tasks.md`.
2. Show the current goal, the requested replacement, and the exact project
   memory files that would change.
3. Require a separate explicit confirmation before pausing the current task,
   writing the replacement task, or promoting a future task.
4. After confirmation, make only the approved memory changes in the selected
   project. Never transfer task content to another project. Keep the paused
   task's existing immutable `Task ID:` when moving it into
   `ai/paused-tasks.md`. Give the replacement task
   a concrete immutable `Task ID:` in the
   `TASK-<project-id>-<UTC-date>-<NNN>` form, where `<NNN>` is the next free
   three-digit number for that date in the selected project; never leave a
   placeholder. A promoted future task keeps exactly the same immutable ID
   when it becomes current.
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
memory-isolation rules. It never changes task state during a project switch.
