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

Use the central Obsidian vault at `<hub>/projects/ai-dev-architecture/obsidian-vault`, derived from the confirmed
hub root. The selected board is
`Obsidian/Projects/<project-id>/Kanban.md` inside that vault. Select it by the
confirmed registered project ID and do not ask for a per-project vault path.
Manual board edits are reviewable proposals only. Use these reverse commands
with the mandatory selector:

```text
bash scripts/obsidian-task-sync.sh scan --project-id <confirmed-project-id> --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault
bash scripts/obsidian-task-sync.sh apply --project-id <confirmed-project-id> --confirm-proposal <sha256> --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault
```

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
5. After that approved selected-project task write, invoke the guarded trusted architecture-to-Obsidian refresh
   with `--write --refresh-from-architecture`.
   This direction is trusted only from canonical `ai/` records to generated
   Obsidian views. Keep manifest validation enabled. If it detects a manual
   Obsidian edit, run the local `obsidian-task-sync scan --project-id <confirmed-project-id>` to create its pending
   proposal, report that proposal, and do not overwrite the board.
6. Obsidian-to-`ai/` is a confirmed Obsidian-to-architecture proposal only:
   show its exact status and require `apply --project-id <confirmed-project-id> --confirm-proposal <sha256>` before
   any canonical task write.

## Calendar sync for dated tasks

A task carries a schedule when it has a `Запланировано: <YYYY-MM-DD> <HH:MM>-<HH:MM>`
field or, failing that, a `Due: <YYYY-MM-DD>` field. Whenever an approved write
in this workflow creates, reschedules, or closes such a task, prepare the
matching Apple Calendar change in the same step, under the `hub-calendar`
rules: allowlisted calendar IDs only, the `категория/проект/задача` title form,
and a complete preview showing action, calendar, title, start and end with
timezone, existing event ID, and recurrence scope. A `Запланировано:` field
becomes a timed event; a `Due:` date alone becomes an all-day event on that
date. Creating a task creates the event, changing its schedule updates it, and
closing or dropping the task deletes a future event and leaves a past one
untouched.

Show the exact task-memory diff and that calendar preview together as one
confirmation screen, and treat one user confirmation as approval of exactly the
shown pair. If either part changes, or the calendar preview cannot be built —
the MCP is unreachable, the permission is missing, or the calendar is not in
the allowlist — say which it is, apply neither part, and ask again. A task
without a schedule field produces no calendar item and keeps its usual single
confirmation.

This workflow cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules. It never changes task state during a project switch.
