---
name: hub-task-finish
description: Verify one confirmed registered project's task and, when nothing blocks closure, clean its task memory and save the result in the same step.
---

# Hub Task Finish

Use this skill only after explicit confirmation of a confirmed registered
project and when the user asks to close its task, when the agent has finished
and verified the task in this session (see `## Closing Finished Work` in
`ai/rules/tasks.md`), or for a `close` decision of the morning task check in
`hub-session-scan`; there the cited session evidence is the verification. Its scope is the selected
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
3. If the Done criteria pass, run the `before-task-close` event before
   clearing task context: read `<hub>/ai/modules.md`; for each subscriber
   listed under `before-task-close`, read its rules file and run its command
   for this task of the confirmed project only. A subscriber failure leaves
   the task open and its context intact. With no subscribers, continue.
4. If the check found no blocker, write the changelog entry, any durable
   decision, future-task entries, any reference a subscriber added,
   and the `ai/current-task.md` cleanup. Stop and report instead of writing only when
   the check found a blocker. Before writing, follow `## Write extensions`
   below. An improvement suggested by a subscriber is applied directly,
   reported, and is not a closure blocker.
5. Then save only the selected project's result through its repository and
   report every write, the commit, and whether it was pushed or stayed local.
6. After a write to the selected project's task files, run the
   `after-task-write` event: read `<hub>/ai/modules.md`; for each subscriber
   listed under `after-task-write`, read its rules file and run its command
   for the confirmed project ID only. With no subscribers, do nothing. Apply a
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
memory-isolation rules. Its closure writes remain limited to selected project
`ai/` memory. It never closes, copies, or cleans another project's task memory,
and an optional subscriber offer does not authorize reading or writing
project records.
