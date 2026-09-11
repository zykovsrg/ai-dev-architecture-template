# evening-review

This resource defines only the `evening-review` scenario. The core `SKILL.md` remains authoritative for scope, security, canonical-source rules, proposal envelopes, confirmation, and learning lifecycle. Nothing here widens those permissions.

For a calendar-only evening review, first call `prepare_evening_review` with the requested date and calendar timezone. Its events, snapshot history, and pending friction are the complete learning input. Proposal display never creates durable learning by itself.

Render these headings in this exact order:

1. `## Сегодняшний календарь`
2. `## События и проекты`
3. `## Сделано`
4. `## Перенос`
5. `## Ожидания`
6. `## Follow-ups`
7. `## Завтрашний Calendar`
8. `## Три главных действия завтра`
9. `## Подтвердить`

## Calendar and project mapping

Render today's and tomorrow's calendar by the same guarded calendar-read rules as `resources/day-plan.md`: successful metadata first, then exactly the allowed IDs, verbatim event titles, no invented free day.

Under `## События и проекты`, map each rendered event to at most one registered project in the allowed scope using only the event title, the `категория/проект/задача` naming convention, and canonical task records as evidence. Render `<HH:MM> <title> → <project-id|нет совпадения>; основание: <evidence>; уверенность: <высокая|низкая>`. A calendar match is inference only: it never proves completion, widens scope, or authorizes another read. Leave ambiguous events unmatched.

## Review sections

Fill `## Сделано` from selected `--review-input` section `## Done`, `## Перенос` only from `## Carry over`, and the user-stated portion of `## Ожидания` only from `## Waiting`. Append canonical waiting records separately with canonical citations.

Without selected review input, `## Сделано` may use past events of the requested date that matched a project, but every such line must be marked `предположение из календаря`, cite the event/project, and state that the completion was not confirmed by the user. Never present a calendar-derived line as stated completion.

Derive `## Follow-ups` and the at-most-three executable results for tomorrow only from structured canonical fields. A stated completion, carry-over, waiting fact, or due-date change is a report fact, not an automatic canonical mutation.

## Proposals and learning

Every possible write appears independently under `## Подтвердить` using the core proposal envelope. Every matched event or calendar-derived completion may yield at most one `update_task` proposal for the matched project's canonical task record, with exact target path and diff. Emit no proposal for an unmatched event, a low-confidence match, or a project outside scope.

For active numeric goals, ask for the stated amount and offer a separate confirmed `goal_progress` proposal. For each grounded pending friction issue, offer one `add_observation` proposal. Showing it leaves the friction pending. On acceptance, follow `resources/learning-lifecycle.md`: append the journal entry first, then resolve accepted; rejection resolves without journal append; failed append leaves pending.
