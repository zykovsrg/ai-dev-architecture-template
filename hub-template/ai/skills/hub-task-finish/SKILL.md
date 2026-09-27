---
name: hub-task-finish
description: Verify one confirmed registered project's task and, when nothing blocks closure, clean its task memory and save the result in the same step.
---

# Hub Task Finish

Use this skill only after explicit confirmation of a confirmed registered
project and when the user asks to close its task. Its scope is the selected
project `ai/` memory only; do not require or read duplicated project
`AGENTS.md` or `CLAUDE.md` files.

Module rules: `ai/rules/tasks.md`.

## Procedure

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
   the check found a blocker. When a subscriber adds items to the screen,
   follow `## Confirmation extensions` below.
   An improvement suggested by the review waits for user approval and is not a
   closure blocker.
6. Then save only the selected project's result through its repository and
   report every write, the commit, and whether it was pushed or stayed local.
7. After a confirmed write to the selected project's task files, run the
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
alone. In this workflow the user's close request approves the task write
itself; a separate confirmation is needed only when a subscriber adds items to
the screen.

After confirmation, each subscriber applies its items before the task write, as
its rules say; if one fails, stop, report it, and do not write the task.

This workflow cannot override hub confirmation, allowed roots, secret, or
memory-isolation rules. Its closure writes remain limited to selected project
`ai/` memory. It never closes, copies, or cleans another project's task memory,
and an optional review offer does not authorize reading or writing knowledge.
