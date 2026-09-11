# day-plan

This resource defines only the `day-plan` scenario. The core `SKILL.md` remains authoritative for scope, security, canonical-source rules, proposal envelopes, confirmation, and learning lifecycle. Nothing here widens those permissions.

Read `resources/calendar-context.md` on every run. Day planning may maintain that local noncanonical calendar context buffer; calendar events and project task records still require their normal confirmation boundaries.

A successful `day-plan` renders these headings in this exact order:

1. `## Текущий календарь`
2. `## Конфликты`
3. `## Задачи вне календаря`
4. `## Просроченные задачи`
5. `## Предлагаемый календарь`
6. `## Рекомендации`

If the local context buffer was written, replace the core no-changes line with exactly `Обновлён локальный контекст; календарь и задачи не изменены.`

## Calendar rendering

Under `## Текущий календарь`, first call `list_calendar_metadata`. Only after a successful response call `read_events` with exactly the returned calendar IDs and the calendar timezone. Render each event separately, in start order, as `- <HH:MM>–<HH:MM> — <title>`. Include the calendar name only when needed to disambiguate. Keep event titles verbatim: do not shorten, translate, group, or paraphrase them.

Never call `read_events` before successful metadata. If the MCP is unreachable, permission is missing, or the allowlist is empty, state which condition occurred rather than inventing an empty schedule. Do not report an empty allowlist without a successful metadata response and never claim a free day you could not read. On `CALENDAR_NOT_ALLOWED`, read the local allowlist file and retry with exactly its IDs; report an empty allowlist only when that file is confirmed empty.

## Conflicts and task sections

Under `## Конфликты`, list only grounded overlaps between calendar events or between an event/task and another task that carries an exact `Запланировано:` range. Cite both records. A task without an exact range does not prove a conflict. Render `- Нет.` when none is grounded.

Under `## Задачи вне календаря`, render ranked actionable tasks that have neither an exact `Запланировано:` range for the requested date nor a grounded calendar match. Exclude overdue tasks. Use `<result> — <project-id>; срок: <YYYY-MM-DD|нет>; источник: <canonical-path>`.

Under `## Просроченные задачи`, render every actionable task due before the requested date as `<exact canonical task title> — <project-id>; срок: <YYYY-MM-DD>; просрочено: <N> дн.; источник: <canonical-path>`. Use the exact canonical task title, never a generated summary. Do not repeat a task in another day-plan section.

## Proposed calendar

Under `## Предлагаемый календарь`, render one chronological view containing every existing event plus proposed blocks for the highest-ranked unscheduled or overdue tasks that fit. Every entry is a separate bullet:

`- <HH:MM>–<HH:MM> — <title>; статус: <сохраняется|предлагается>; основание: <calendar|canonical-path>; duration: stated|estimate`

Use a stated duration when present in the canonical task; otherwise mark `estimate`. Apply learned rules and active numeric goal progress as planning constraints without adding another output section. Never remove an existing event or invent a time merely to fit work. Put work that cannot fit under `Не вошло`. Retained events keep their calendar titles verbatim; proposed blocks use exact canonical task titles. The proposed calendar is read-only until the separate `hub-calendar` preview/confirmation path is completed.

## Editing the plan

After rendering, every user statement that changes or adds work becomes a proposal in the same reply. Map exactly one grounded statement to exactly one action:

| Statement | Envelope action |
|---|---|
| Work is done, built, sent, or otherwise advanced | `update_task` |
| The due date moves | `update_due` |
| A wait starts, changes, or ends | `update_waiting` |
| New work or a reminder is named | `create_task` |
| A block time or duration changes | `calendar-event` |

Preserve the exact user-stated task title unless the user explicitly replaces it. Each proposal keeps its own exact target and diff. When a task carries a schedule, emit its complete calendar preview beside the task diff; one confirmation may approve only that exact shown pair under `hub-calendar`. A selectable package may span active projects, but every proposal retains its own project ID, `target_path`, and diff.

Do not guess project ownership. If one active registered project cannot be identified, ask which project owns the statement and emit no task/calendar proposal. If the canonical record already contains the statement, say so rather than emitting an empty diff.

## Recommendations and validation

Under `## Рекомендации`, use `resources/calendar-context.md` to analyze the past 30 days and next 14 days and suggest grounded actions for today. Keep this sixth section even if context is unavailable and state the limitation.

Before sending the result, pass the complete draft on stdin to `scripts/validate-day-plan-output.py`. Send only after it exits successfully; otherwise rewrite and validate again. A cache-write failure never permits omitting `## Рекомендации`.
