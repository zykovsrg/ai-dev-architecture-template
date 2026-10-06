# Planning Module Rules

## before-task-write

A task carries a schedule when it has a `Запланировано: <YYYY-MM-DD> <HH:MM>-<HH:MM>`
field or, failing that, a `Due: <YYYY-MM-DD>` field. Whenever the pending task
write from the workflow that fired this event creates, reschedules, or closes
such a task, prepare the
matching Apple Calendar change in the same step, under the `hub-calendar`
rules: allowlisted calendar IDs only, the nested Cyrillic title from `scripts/archiprojects.py calendar-title`,
and a complete preview showing action, calendar, title, start and end with
timezone, existing event ID, and recurrence scope. A `Запланировано:` field
becomes a timed event; a `Due:` date alone becomes an all-day event on that
date. Creating a task creates the event, changing its schedule updates it, and
closing or dropping the task deletes a future event and leaves a past one
untouched. After the event is created or moved, the same task write
writes or refreshes the `Событие:` link line from `ai/skills/hub-task-intake/resources/task-record-format.md`;
closing or dropping removes it together with the future event.

Apply both parts without asking the user, except when the calendar part is a
deletion: then show the task diff and the delete preview and wait for one
explicit yes. If the calendar preview cannot be built — the MCP is
unreachable, the permission is missing, or the calendar is not in the
allowlist — say which it is and write neither part. A task without a schedule
field produces no calendar item.

Apply the calendar change once, then apply the task write, including the
`Событие:` line. If the calendar
apply fails, write nothing to the task, report it, and never retry a create.
Details are in `## Joint task and calendar change`.

## Joint task and calendar change

For a dated task change that arrives as a pending proposal from an `after-task-write` subscriber, first validate the pending proposal and
prepare its exact task diff. Use only guarded Calendar tools to identify the
event and build its preview (calendar, event ID, timezone, dates, recurrence
scope). Without asking the user (unless the calendar part is a deletion),
recheck hashes, apply the calendar change once, then apply the exact task proposal and
run the `after-task-write` event (see `ai/modules.md`). If any step fails, preserve the proposal and report
the completed partial step; never silently retry a calendar create. After the
calendar change succeeds, write or refresh the task's `Событие:` link line in
the same task write.

## after-calendar-change

After a successful `apply_change`, re-read the affected day through
`read_events` and pass its events to
`bash scripts/snapshot-calendar.sh --hub <hub> --at <affected-date>-<HHMM>`.
Use one `HH:MM|HH:MM|<title>|<calendar>` line per event in start-time order.
This is a noncanonical cache, and a snapshot
failure must be reported without undoing the already applied calendar change.

## Plans and reviews

Evening review defaults to a guided conversation: first display tomorrow's
events from the exact allowed calendar `Важно и срочно`, then ask one question
per turn about today's events with an unambiguous active registered project.
Skip events without projects silently. Repeated blocks of an answered task
are consumed together; distinct tasks in one project remain separate.
`scripts/evening_review.py` prepares the read-only urgent list, event queue and
the mandatory [D-30, D+31) sync check; its first run fails without that window.
The scenario's old full-report headings apply only when explicitly requested.
Explicit user corrections to projectless Calendar events remain authorized.

Use the hub-owned `hub-workflows` skill for `day-plan`, `evening-review`, and
`weekly-review`, and `hub-task-overview` for `capture`. The skill performs semantic AI analysis, while
the optional Bash adapter only validates mechanical scope, paths, and recorder
JSON. Suggested blocks in a plan are suggestions, not writes; when the user
accepts them or states a change, the skill applies it without a further
confirmation step.

The day-plan chat output has exactly three sections in this order: current
calendar, synchronization, and overdue actionable tasks. Overdue tasks are
always last. Do not add task-outside-calendar or recommendation sections.
Synchronize unambiguous task times from Calendar before composing the plan,
validate writes and reload changed canonical task records before ranking or
rendering them. Calendar is the source of truth for time, not deadlines or
completion. After joint edits, verify affected dates and task records only.
This runs on a requested day plan, without a scheduled automation or reminder.
Render existing calendar titles verbatim, chronologically, one entry per line.
Learned rules and numeric goal progress support joint planning without adding
extra chat sections.

All-day events are calendar events too: day planning and evening review render
each one separately as `весь день — <exact title>`. They never group,
paraphrase, or interpret an all-day title. Calendar events never prove completion.
A direct, unambiguous user decision that a known task is complete,
moved, or waiting is applied at once to the canonical task record and, when
the schedule changes, to the calendar; then report it briefly. Deleting a
future event still waits for an explicit yes. An ambiguous task reference
creates no mutation; ask which task is meant.

An explicit new action or reminder stated during day planning is not merely a
calendar item: when it belongs to one confirmed project, `hub-workflows`
creates an exact `create_task` or `update_task` proposal for that project's
canonical task record and a paired timed calendar event, and applies both
without asking. Relative and
explicit dates are resolved in the calendar timezone. An explicit interval is
preserved; a date-only statement uses the first free 30-minute interval without
moving an existing event. The task diff records
`Запланировано: YYYY-MM-DD HH:MM-HH:MM` and the matching event is created. A past date never
implies completion. The task proposal uses the exact stated title and has its
own exact target path and diff. The workflow never guesses the owning project.
It asks the user to identify one confirmed project when the action is ambiguous,
and writes neither task nor event until then. Every overdue task is
rendered with its exact canonical task title, never a generated summary or
translation.

Clear day-planning requests, including «распланируем сегодняшний день»,
«распланируем остаток дня», «план на сегодня», «план на остаток дня», and
"plan today", invoke `hub-workflows` before any reply. Their
reply uses the three mandatory day-plan sections; a free-form calendar summary
is not a valid day-plan response.

The general 5-line and 80-word output default does not apply to a day plan.
Every day-plan response renders all three headings, even when a section contains
only `- Нет.` or a precise data-access limitation.

Day planning maintains local `ai/tmp/calendar-context.json`: 30 past days,
today and 30 future days. Initial guarded reads populate it; subsequent runs
prune expired days and fetch missing far-future days. Joint planning uses the
past month and next 14 days with canonical tasks and verified deadlines.
The detailed lifecycle is in `hub-workflows/resources/calendar-context.md`.
This noncanonical cache exception allows local context writes only; event
data is never published, and no background job or automatic task write is added.

`ai/workflow-context.md` contains the learned rules that `day-plan` and
`evening-review` read, with at most 100 rules. `hub-workflows` writes
`ai/workflow-context.md` and `ai/workflow-observations.md` directly and then
reports what changed; removing a learned rule needs an explicit yes. `scripts/snapshot-calendar.sh` writes snapshots after
calendar changes and at the start of day and evening reviews.
