# All-day events and task-state synchronization

## Goal

Day planning and evening review must render all-day calendar events verbatim,
one event per line. A user decision about a known task—completion, due-date
move, or waiting-state change—must produce an exact canonical task-record
change alongside any related calendar change, so the calendar and architecture
do not drift.

## Scope

- `day-plan` and `evening-review` render all-day events with their exact title
  and an explicit all-day marker; they never group, shorten, or interpret them.
- Both workflows identify direct user statements about a known task as proposed
  `update_task`, `update_due`, or `update_waiting` changes.
- A proposal contains the project ID, canonical task-record path, and an exact
  diff. A calendar move contains its complete guarded calendar preview.
- One explicit confirmation applies only the displayed, unchanged task diff and
  its paired calendar change. Calendar-only edits remain calendar-only.

## Non-goals

- Calendar events never prove a task is complete.
- No task is changed from a vague or ambiguous statement.
- The workflows do not automatically apply a proposal before the user confirms
  the exact displayed change.

## Design

### All-day rendering

Use the same calendar event list already returned by the guarded read. Render
each all-day event as a separate bullet with the verbatim title and `весь день`.
Timed events retain the existing `HH:MM–HH:MM` form. The proposed-calendar
section preserves all-day events in the same way.

### Decision-to-record synchronization

For a user statement that clearly names one canonical task:

| Statement | Canonical change |
| --- | --- |
| "сделано" / "выполнено" | mark the task done and record the completion date |
| "перенести на <date>" | update the task due date; pair a calendar move when one exists |
| "жду <person>" / "ответ получен" | update or clear the structured waiting fields |

The workflow must resolve the task through canonical records, not calendar-title
similarity alone. If more than one task matches, it asks the user which task is
meant and creates no proposal.

### Confirmation and application

The response presents each exact task diff and, when relevant, the calendar
preview. A single confirmation applies the named package only. After a
successful application, the workflow re-reads the affected canonical record
and calendar day and reports the synchronized result.

## Tests

- Day-plan and evening-review fixtures contain multiple all-day events and
  assert that every exact title appears separately.
- Tests reject grouped or paraphrased all-day output.
- Tests cover completion, due-date move, and waiting-state updates in both
  workflows, including exact task diffs and paired calendar previews.
- Tests cover an ambiguous task reference and require no mutation proposal.

## Acceptance criteria

1. A day plan and evening review never omit or paraphrase an all-day event.
2. A confirmed completion or transfer is reflected in the canonical task record
   and, where applicable, its calendar event.
3. Calendar-derived activity remains an inference and does not close a task.
4. Existing calendar and task confirmation safeguards remain intact.
