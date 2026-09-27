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
writes or refreshes the `Событие:` link line from task-record-format.md;
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
