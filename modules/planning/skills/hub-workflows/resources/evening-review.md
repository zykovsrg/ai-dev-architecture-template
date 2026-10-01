# evening-review

This resource defines only the `evening-review` scenario. The core `SKILL.md` remains authoritative for scope, security, canonical-source rules, proposal envelopes, write policy, and learning lifecycle. Nothing here widens those permissions.

For a calendar-only evening review, call `list_calendar_metadata` first, then
`read_events` for the requested date and calendar timezone over the allowed
calendar IDs. Its events are the calendar learning input. Proposal display
never creates durable learning by itself.

Inspect `availability_complete` and `unavailable_calendar_ids` in every
calendar response. If coverage is incomplete, name the unavailable calendar
IDs and do not infer absence or completion from them. Skip calendar-task sync
for a partial window.

If coverage is complete, pipe one `HH:MM|HH:MM|<title>|<calendar>` line per
event, in start-time order, to
`bash scripts/snapshot-calendar.sh --hub <hub> --at <date>-<HHMM>`. List prior
snapshots for the day with
`bash scripts/snapshot-calendar.sh --hub <hub> --list --day <date>`.

Read pending friction only when `learning` is listed in `ai/modules.md`, with
`python3 scripts/workflow_friction.py --hub <hub> list --day <date>`.

Render these headings in this exact order:

1. `## Сегодняшний календарь`
2. `## События и проекты`
3. `## Ожидания`
4. `## Follow-ups`
5. `## Завтрашний Calendar`
6. `## Подтвердить`

## Calendar and project mapping

Render today's and tomorrow's calendar by the same guarded calendar-read rules as `resources/day-plan.md`: successful metadata first, then exactly the allowed IDs, verbatim event titles, no invented free day. Render each all-day event separately as `- весь день — <title>`. Keep event titles verbatim: do not shorten, translate, group, or paraphrase them.

Under `## События и проекты`, map each rendered event to at most one registered project in the allowed scope using only the event title, the `категория/проект/задача` naming convention, and canonical task records as evidence. Render `<HH:MM> <title> → <project-id|нет совпадения>; основание: <evidence>; уверенность: <высокая|низкая>`. A calendar match is inference only: it never proves completion, widens scope, or authorizes another read. Leave ambiguous events unmatched.

## Review sections

Fill the user-stated portion of `## Ожидания` only from selected `--review-input` section `## Waiting`. Append canonical waiting records separately with canonical citations.

A selected review input may also carry `## Done` and `## Carry over`. The review renders no section for them: a stated completion or carry-over becomes an `update_task` or `update_due` proposal under `## Подтвердить` and appears nowhere else. Never list stated or calendar-derived completions as narrative output.

Derive `## Follow-ups` only from structured canonical fields. A stated completion, carry-over, waiting fact, or due-date change is applied to the canonical record at once and reported.

## Proposals and learning

Every possible write appears independently under `## Подтвердить` using the core proposal envelope. Every matched event or stated completion may yield at most one `update_task` proposal for the matched project's canonical task record, with exact target path and diff. Emit no proposal for an unmatched event, a low-confidence match, or a project outside scope.

For a direct, unambiguous user statement about one canonical task, apply exactly
one `update_task`, `update_due`, or `update_waiting` change with the project
ID, exact target path, and exact diff. Pair a calendar change only when the
task schedule changes. If the task reference is ambiguous, change nothing and
ask which task is meant. Otherwise apply the canonical task-record diff and
its paired calendar change at once and report them.

Only when `goals` is listed in `ai/modules.md`, for active numeric goals ask for the stated amount and record the stated amount as a `goal_progress` entry directly.

For each grounded pending friction issue, offer one `add_observation` proposal. Proposal display must leave that observation pending; all acceptance, rejection, journal ordering, and append-failure behavior is defined only in `resources/learning-lifecycle.md`.

Run the same sync check as `resources/day-plan.md` "Sync section" and render
its items under `## Подтвердить` with the same mapping and gates.
