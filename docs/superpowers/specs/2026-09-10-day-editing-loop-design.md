# Day editing loop design

## Purpose

Make the interactive day-editing loop reproducible by any AI agent, not only by
the one that happens to infer it. The current specification defines how a day
plan is rendered but not what happens after rendering, and it contradicts
itself in three places. A second agent following the same files answered in
prose, prepared no task diffs, demanded a project switch for a single task
write, and left one of two projects unwritten.

The observed behavior gap, not a style preference, is the subject of this
design.

## Scope

Canonical sources only:

- `hub-template/ai/skills/hub-workflows/SKILL.md`
- `hub-template/ai/skills/hub-calendar/SKILL.md`

The installed hub copy is produced from these by the project's existing sync
path. No other skill, script, or project file changes.

## Rules to preserve

- Every calendar write keeps a complete, fresh, single-use preview.
- Nothing is applied without a confirmation that names what is being applied.
- The personal-assistant read scope stays read-only for everything except the
  three canonical task records named below.
- Project code, knowledge records, credentials, and inactive projects stay
  unreadable in this scope.
- Proposal envelopes keep their exact `target_path` and exact diff.

## The loop to specify

After the day plan is rendered, the user names a task and states a fact about
it: it was done yesterday, it will not fit today and moves to Friday, a call
was cancelled and voice notes arrive by tomorrow, a meeting is 30 minutes, put
it at 16:30.

For each such statement, in the same reply, the agent must:

1. map the statement to exactly one canonical task record in one active
   registered project;
2. emit the exact diff for that record with its exact `target_path`, using the
   envelope action that matches the statement;
3. when the task carries a schedule, emit the complete calendar preview beside
   that diff;
4. allow the pair — task diff plus calendar preview — to be applied by one
   confirmation;
5. gather statements that touch several projects into one selectable proposal
   package rather than one confirmation per project.

If a statement cannot be grounded in exactly one project, ask which project
owns it and emit no proposal until the user answers.

## Defects to fix

### D1 — status statements are not covered

`hub-workflows/SKILL.md:209` covers only "a new action or reminder for today".
The dominant case during day editing is a status change to an existing task:
done, built, due date moved, a new waiting record, a changed duration. Nothing
maps those to an envelope, so the agent answers in prose.

Fix: extend the rule to status statements and state which envelope action
matches which kind of statement.

| Statement | Envelope action |
|---|---|
| Работа по задаче сделана | `update_task` |
| Срок сдвигается | `update_due` |
| Появилось или закрылось ожидание | `update_waiting` |
| Названо новое действие | `create_task` |
| Изменилось время или длительность блока | `calendar-event` |

### D2 — the scope contradiction

`hub-workflows/SKILL.md:32-46` gives a day plan an all-active-project scope.
`hub-workflows/SKILL.md:209` then requires "the confirmed project that owns the
action", and `hub-workflows/SKILL.md:322-330` requires that a package "can be
applied only by its owning confirmed project workflow". A day plan has no
confirmed project by definition, so the two later rules cannot be satisfied.
This is the root cause of the confirmation cascade and of the second project
being dropped.

Decision (user, 2026-09-10): a day-plan proposal applies without a project
switch, and one package may write into several projects.

Fix: state the write scope explicitly and bound it.

- A confirmed day-plan package may write only `ai/current-task.md`,
  `ai/future-tasks.md`, and `ai/paused-tasks.md` of active registered projects.
- Every proposal in the package shows its project ID, exact `target_path`, and
  exact diff before confirmation.
- No other file, path, or project state may be written from this scope.
- A project switch remains required for any richer project work.

The traded protection is named on purpose: one confirmation can now change
files in several projects the user did not open. The exact-path display and the
three-file limit are the compensating controls.

### D3 — no package for the day plan

`hub-workflows/SKILL.md:315-318` grants a selectable package to `capture` only,
while `hub-workflows/SKILL.md:213` declares day-plan proposals independently
selectable. The agent therefore asks per proposal.

Fix: grant the day plan the same selectable package. One confirmation names the
proposals that remain selected; the user may exclude individual proposal IDs;
any changed diff needs a new confirmation.

### D4 — the merged gate excludes the day plan

`hub-calendar/SKILL.md:35-40` merges the task diff and the calendar preview into
one confirmation for `hub-task-intake`, `hub-task-switch`, and
`hub-task-finish`. `hub-workflows` is absent, so a day plan cannot pair them.

Fix: add `hub-workflows` to that exception with the existing limits unchanged —
the preview stays complete, an unshown or changed event still needs its own
confirmation, and the confirmation dies with the screen it belongs to.

### D5 — a recurring preview looks unsafe

`hub-calendar/SKILL.md:47-51` requires `this` or `future` scope and the
occurrence start, but does not say that `preview_change` echoes the **series
start date**, not the occurrence being changed. An agent reads the earlier date
as a wrong target and refuses to apply. This cost a full deletion step in the
observed session.

Fix: document the behavior and the recovery.

- A preview whose `start` precedes the requested date identifies a recurring
  series. This is expected, not a mismatch.
- To change one occurrence, send `recurring: true`, `recurrence_scope: this`,
  and `occurrence_start` set to the start of the occurrence being changed.
- A delete preview is the cheap way to learn whether an event is a series
  before proposing a change to it.

### D6 — calendar access is misdiagnosed

`hub-workflows/SKILL.md:163-172` forbids reporting an empty allowlist without a
successful metadata response, but gives no way to learn which IDs are allowed.
The observed agent reported an empty allowlist, then read the calendar
successfully on retry.

Fix: specify the order.

1. Call `list_calendar_metadata`.
2. On `CALENDAR_NOT_ALLOWED`, read the local allowlist file and use exactly the
   IDs it lists.
3. Report an empty allowlist only when that file is confirmed empty.
4. Never claim a free day that could not be read.

## Acceptance criteria

- An agent reading only the two skill files performs the loop above without
  extra prompting.
- "Эта задача сделана вчера" produces a task-record diff, not prose.
- A day-plan task write requires no project switch.
- Statements touching three projects produce one package and one confirmation.
- A recurring-event move is not refused because the preview shows the series
  start.
- No edit weakens the preview, the read boundary, or the no-auto-apply rule.

## Out of scope

- Ranking, section order, and the six day-plan headings stay as they are.
- Evening review, weekly review, and capture formats are untouched.
- No change to goal counting, learning lifecycle, or session review.
