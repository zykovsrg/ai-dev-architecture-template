# Planning Module Rules

## before-task-confirmation

A task carries a schedule when it has a `Запланировано: <YYYY-MM-DD> <HH:MM>-<HH:MM>`
field or, failing that, a `Due: <YYYY-MM-DD>` field. Whenever the pending task
write from the workflow that fired this event creates, reschedules, or closes
such a task, prepare the
matching Apple Calendar change in the same step, under the `hub-calendar`
rules: allowlisted calendar IDs only, the `категория/проект/задача` title form,
and a complete preview showing action, calendar, title, start and end with
timezone, existing event ID, and recurrence scope. A `Запланировано:` field
becomes a timed event; a `Due:` date alone becomes an all-day event on that
date. Creating a task creates the event, changing its schedule updates it, and
closing or dropping the task deletes a future event and leaves a past one
untouched. After the event is created or moved, the same confirmed task diff
writes or refreshes the `Событие:` link line from `ai/skills/hub-task-intake/resources/task-record-format.md`;
closing or dropping removes it together with the future event.

Show the exact task-memory diff and that calendar preview together as one
confirmation screen, and treat one user confirmation as approval of exactly the
shown pair. If either part changes, or the calendar preview cannot be built —
the MCP is unreachable, the permission is missing, or the calendar is not in
the allowlist — say which it is, apply neither part, and ask again. A task
without a schedule field produces no calendar item and keeps the calling
workflow's usual confirmation behaviour.

After the one confirmation, recheck the preview, apply the calendar change
once, then apply the task write, including the `Событие:` line. If the calendar
apply fails, write nothing to the task, report it, and never retry a create.
Details are in `## Joint task and calendar change`.

## Joint task and calendar change

For a dated task change that arrives as a pending proposal from an `after-task-write` subscriber, first validate the pending proposal and
prepare its exact task diff without writing. Use only guarded Calendar tools to
identify the event and show one preview containing the task diff, calendar,
event ID, timezone, dates and recurrence scope. After confirmation, recheck
hashes, apply the calendar change once, then apply the exact task proposal and
run the `after-task-write` event (see `ai/modules.md`). If any step fails, preserve the proposal and report
the completed partial step; never silently retry a calendar create. After the
calendar change succeeds, write or refresh the task's `Событие:` link line in
the same task write.

## after-calendar-change

After a successful `apply_change`, re-read the affected day through
`read_events` and pass its events to
`bash scripts/snapshot-calendar.sh --hub <hub> --at <affected-date>-<HHMM>`.
Use one `HH:MM|HH:MM|<title>|<calendar>` line per event in start-time order.
This is a noncanonical cache, needs no additional confirmation, and a snapshot
failure must be reported without undoing the already applied calendar change.

## Plans and reviews

Use the hub-owned `hub-workflows` skill for `day-plan`, `evening-review`, and
`weekly-review`, and `hub-task-overview` for `capture`. The skill performs semantic AI analysis, while
the optional Bash adapter only validates mechanical scope, paths, and recorder
JSON. Neither layer applies project, task, knowledge, waiting, deadline,
Calendar, or vault changes.

The day-plan chat output has exactly six sections in this order: current
calendar, grounded conflicts, actionable project tasks that are not in that
calendar, overdue actionable tasks, one proposed calendar, and recommendations. A task appears
in only one task section. The proposed calendar retains existing events and
labels every suggested block's duration as stated or estimated; it lists work
that does not fit instead of silently dropping it. Both calendars are
chronological bullet lists: one `time — event` entry per line. Learned rules
and numeric goal progress constrain the proposal without creating extra chat
sections. Existing calendar titles are copied verbatim; proposed new blocks use
the exact title of their canonical task and never a generated summary.

All-day events are calendar events too: day planning and evening review render
each one separately as `весь день — <exact title>`. They never group,
paraphrase, or interpret an all-day title. Calendar events never prove completion.
A direct, unambiguous user decision that a known task is complete,
moved, or waiting produces an exact canonical task-record diff and, only when
the schedule changes, its complete guarded calendar preview. The exact package
applies only after the user confirms it; an ambiguous task reference creates no
proposal or mutation.

An explicit new action or reminder stated during day planning is not merely a
calendar item: when it belongs to one confirmed project, `hub-workflows`
creates an exact `create_task` or `update_task` proposal for that project's
canonical task record and a paired timed calendar proposal. Relative and
explicit dates are resolved in the calendar timezone. An explicit interval is
preserved; a date-only statement uses the first free 30-minute interval without
moving an existing event. The task diff records
`Запланировано: YYYY-MM-DD HH:MM-HH:MM`, and its complete calendar preview is
shown beside it. One confirmation covers exactly that pair. A past date never
implies completion. The task proposal uses the exact stated title and has its
own exact target path and diff. The workflow never guesses the owning project.
It asks the user to identify one confirmed project when the action is ambiguous,
and emits neither task nor calendar proposal until then. Every overdue task is
rendered with its exact canonical task title, never a generated summary or
translation.

Clear day-planning requests, including «распланируем сегодняшний день»,
«распланируем остаток дня», «план на сегодня», «план на остаток дня», and
"plan today", invoke `hub-workflows` before any reply. Their
reply uses the six mandatory day-plan sections; a free-form calendar summary
is not a valid day-plan response.

The general 5-line and 80-word output default does not apply to a day plan.
Every day-plan response renders all six headings, even when a section contains
only `- Нет.` or a precise data-access limitation.

Day planning maintains local `ai/tmp/calendar-context.json`: 30 past days,
today and 30 future days. Initial guarded reads populate it; subsequent runs
prune expired days and fetch missing far-future days. Recommendations use the
past month and next 14 days with canonical tasks and verified deadlines.
The detailed lifecycle is in `hub-workflows/resources/calendar-context.md`.
This noncanonical cache exception allows local context writes only; event
data is never published, and no background job or automatic task write is added.

`ai/workflow-context.md` contains the learned rules that `day-plan` and
`evening-review` read, with at most 100 rules. `hub-workflows` writes
`ai/workflow-context.md` and `ai/workflow-observations.md` only through a
confirmed proposal. `scripts/snapshot-calendar.sh` writes snapshots after
calendar changes and at the start of day and evening reviews.
