# Joint task and calendar change

For a dated task change that arrives as a pending proposal from an `after-task-write` subscriber, first validate the pending proposal and
prepare its exact task diff without writing. Use only guarded Calendar tools to
identify the event and show one preview containing the task diff, calendar,
event ID, timezone, dates and recurrence scope. After confirmation, recheck
hashes, apply the calendar change once, then apply the exact task proposal and
run the `after-task-write` event (see `ai/modules.md`). If any step fails, preserve the proposal and report
the completed partial step; never silently retry a calendar create. After the
calendar change succeeds, write or refresh the task's `Событие:` link line in
the same task write.
