---
name: hub-task-finish
description: Verify one confirmed registered project's task and, when nothing blocks closure, clean its task memory and save the result in the same step.
---

# Hub Task Finish

Use this skill only after explicit confirmation of a confirmed registered
project and when the user asks to close its task. Its scope is the selected
project `ai/` memory only; do not require or read duplicated project
`AGENTS.md` or `CLAUDE.md` files.

## Procedure

Use the central Obsidian vault at `<hub>/projects/ai-dev-architecture/obsidian-vault`, derived from the confirmed
hub root. The selected board is
`Obsidian/Projects/<project-id>/Kanban.md` inside that vault. Select it by the
confirmed registered project ID; never ask for a per-project vault path.
Manual board edits remain reviewable proposals, not direct canonical writes.
Use these reverse commands with the mandatory selector:

```text
bash scripts/obsidian-task-sync.sh scan --project-id <confirmed-project-id> --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault
bash scripts/obsidian-task-sync.sh apply --project-id <confirmed-project-id> --confirm-proposal <sha256> --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault
```

1. Read the selected project's `ai/current-task.md` and the smallest relevant
   `ai/decisions.md`, `ai/changelog.md`, or `ai/future-tasks.md` file.
2. Check recorded Done criteria and report any missing verification or open
   risk. Do not change task memory during this check.
   Run the deterministic task-record and review checks before any model call;
   report a deterministic failure directly and leave the task open.
3. If the Done criteria pass, run `hub-session-review` for this task's current
   visible session before clearing task context. Save and validate the review,
   then add `Session review: ai/session-reviews/<file>.md` to the task so a
   closure retry can reuse it. A review-write failure leaves the task open and
   its context intact. Partial history is recorded honestly and does not alone
   block closure. Do not review the review or closure output again here.
4. After the review, if durable records linked from this task may need a focused
   check, the agent may offer `hub-knowledge-review`, but must never start it
   automatically. Declining it has no effect on closure.
5. If the check found no blocker, write the changelog entry, any durable
   decision, confirmed future-task entries, the review reference, and the
   `ai/current-task.md` cleanup. Stop and report instead of writing only when
   the check found a blocker. A task with a schedule field keeps the single
   joint confirmation below, because its closure also changes the calendar.
   An improvement suggested by the review waits for user approval and is not a
   closure blocker.
6. Then save only the selected project's result through its repository and
   report every write, the commit, and whether it was pushed or stayed local.
7. After a selected-project task write, invoke the guarded trusted architecture-to-Obsidian refresh with
   `bash scripts/generate-obsidian-projects-kanban.sh --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault --write --refresh-from-architecture`.
   This direction is trusted only from canonical `ai/` records to generated
   Obsidian views. Keep manifest validation enabled. If it detects a manual
   Obsidian edit, run the local `obsidian-task-sync scan --project-id <confirmed-project-id>` to create its pending
   proposal, report that proposal, and do not overwrite the board.
8. Obsidian-to-`ai/` is a confirmed Obsidian-to-architecture proposal only:
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
without a schedule field produces no calendar item, so its closure needs no
confirmation at all.

This workflow cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules. Its closure writes remain limited to selected project
`ai/` memory. It never closes, copies, or cleans another project's task memory,
and an optional review offer does not authorize reading or writing knowledge.
