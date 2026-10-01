# Goals Module Rules

## Ownership And Registry

- `ai/goals.md` is the canonical hub-owned numeric goal registry; each goal
  references a group in `ai/archiprojects.md` via `group`.
- `ai/goal-log.md` is the canonical hub-owned progress log for numeric goals.

## Goal Progress

Numeric goals live in `ai/goals.md` as blocks with `group`, `target`, `unit`,
and `due`; `group` must name a known group in `ai/archiprojects.md`. Their
progress lives in the canonical `ai/goal-log.md`, one line per event: date,
goal id, amount in the goal's unit, optional project, optional note. Adding a
goal is a registry change only; the counter, the evening question, and the
weekly figures follow from it with no further edit.

`scripts/count-goal-progress.sh` is the only computation of progress, pace, and
forecast, and the only validator of the log. Workflows render its output
verbatim and never recompute it. `hub-goal-progress` is the only writer of
`ai/goal-log.md`; it appends one line with the amount the user stated, without asking again. An amount is never
inferred from a task or calendar event.
