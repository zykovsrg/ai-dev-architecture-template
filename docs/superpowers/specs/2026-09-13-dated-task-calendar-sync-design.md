# Dated task and calendar synchronization

## Goal

When the user says that named work should be done on any resolved date, create
one proposed change that updates the owning project task and creates a timed
Apple Calendar block. This applies equally to relative dates such as
"yesterday", "tomorrow", and "next week", and to explicit calendar dates.

## Chosen design

The day-planning workflow resolves the stated date in the calendar timezone.
If the user supplies a time or time range, preserve it. If they supply a date
without a time, find a free interval on that date and propose a 30-minute
block. The task record stores the resulting interval as
`Запланировано: YYYY-MM-DD HH:MM-HH:MM`.

The task-record diff and the complete calendar preview form one package. A
single explicit confirmation applies exactly that pair; failure to build either
part applies neither. The created event follows the existing lower-case
`категория/проект/задача` title rule. The workflow never silently moves an
existing event to make room.

Dates in the past are handled in the same way: the task and event retain that
past date, but no completion is inferred from the scheduled block.

## Alternatives rejected

1. Create an all-day event for a date without a time. It does not reserve an
   actionable time window.
2. Require the user to provide a time every time. It creates unnecessary
   planning friction.
3. Use a fixed default clock time. It can collide with the actual calendar.

## Acceptance criteria

- Relative and explicit date phrases are resolved using the calendar timezone.
- A date-only request produces a 30-minute free-slot proposal.
- An explicit interval is kept unchanged.
- The task schedule and the calendar preview appear together and apply
  atomically after confirmation.
- A past-dated block does not mark the task complete.
- Regression checks cover date-only, explicit-time, and past-date cases.
