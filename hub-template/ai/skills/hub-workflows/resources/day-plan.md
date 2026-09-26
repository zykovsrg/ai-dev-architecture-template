# day-plan

This resource defines only the `day-plan` scenario. The core `SKILL.md` remains authoritative for scope, security, canonical-source rules, proposal envelopes, confirmation, and learning lifecycle. Nothing here widens those permissions.

Read `resources/calendar-context.md` on every run. Day planning may maintain that local noncanonical calendar context buffer; calendar events and project task records still require their normal confirmation boundaries.

A successful `day-plan` renders these headings in this exact order:

1. `## Текущий календарь`
2. `## Задачи вне календаря`
3. `## Просроченные задачи`
4. `## Рекомендации`
5. `## Синхронизация`

If the local context buffer was written, replace the core no-changes line with exactly `Обновлён локальный контекст; календарь и задачи не изменены.`

## Calendar rendering

Under `## Текущий календарь`, first call `list_calendar_metadata`. Only after a successful response call `read_events` with exactly the returned calendar IDs and the calendar timezone. Render each timed event separately, in start order, as `- <HH:MM>–<HH:MM> — <title>`. Render each all-day event separately as `- весь день — <title>`. Include the calendar name only when needed to disambiguate. Keep event titles verbatim: do not shorten, translate, group, or paraphrase them.

Never call `read_events` before successful metadata. If the MCP is unreachable, permission is missing, or the allowlist is empty, state which condition occurred rather than inventing an empty schedule. Do not report an empty allowlist without a successful metadata response and never claim a free day you could not read. On `CALENDAR_NOT_ALLOWED`, read the local allowlist file and retry with exactly its IDs; report an empty allowlist only when that file is confirmed empty.

For each successful `read_events` response, inspect `availability_complete` and `unavailable_calendar_ids`. If coverage is incomplete, render returned events and name unavailable calendar IDs; never interpret missing events as free time. If a calendar-context window read is incomplete, state that synchronization is incomplete and do not use partial data.

## Task sections

Under `## Задачи вне календаря`, render only actionable tasks whose due date equals the requested date and which have neither an exact `Запланировано:` range for that date nor a grounded calendar match. Exclude overdue tasks, undated tasks, and tasks due later: overdue work has its own section and the rest is not today's plan. Use `<result> — <project-id>; срок: <YYYY-MM-DD>; источник: <canonical-path>`. Render `- Нет.` when nothing qualifies.

Under `## Просроченные задачи`, render every actionable task due before the requested date as `<exact canonical task title> — <project-id>; срок: <YYYY-MM-DD>; просрочено: <N> дн.; источник: <canonical-path>`. Use the exact canonical task title, never a generated summary. Do not repeat a task in another day-plan section.

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

For a direct, unambiguous user statement about one canonical task, emit exactly
one `update_task`, `update_due`, or `update_waiting` proposal with the project
ID, exact target path, and exact diff. Pair a calendar preview only when the
task schedule changes. If the task reference is ambiguous, emit no proposal and
ask which task is meant. After the user confirms the exact displayed package,
apply only that canonical task-record diff and its paired calendar preview.

For a new or changed action with relative and explicit dates, resolve the date
in the calendar timezone. Preserve an explicit interval unchanged. A date-only
statement uses the first 30-minute free interval on that date; never move an
existing event. Put the result in `Запланировано: YYYY-MM-DD HH:MM-HH:MM` in
the exact task diff and show its complete calendar preview beside it; one confirmation may approve only that exact pair. A past date does not infer completion.

Do not guess project ownership. If one active registered project cannot be identified, ask which project owns the statement and emit no task/calendar proposal. If the canonical record already contains the statement, say so rather than emitting an empty diff.

## Sync section

Run sync only when all calendar-context window reads are complete (`availability_complete: true` and no `unavailable_calendar_ids`). Otherwise report that synchronization is incomplete and render no discrepancy items from partial data.

Under `## Синхронизация`, pipe the guarded `read_events` response for the
calendar-context window [D-30, D+31) to
`python3 scripts/calendar_task_sync.py --hub <hub> --now "<YYYY-MM-DD HH:MM>"`.
Render one numbered item per discrepancy in Russian, stating what moved and
from/to times:

- `calendar_moved` → `update_task` proposal: set `Запланировано:` to the event
  time and refresh `синхронизировано`.
- `task_moved` → `calendar-event` update preview to the task time plus the
  task diff refreshing `синхронизировано`.
- `stale_sync` → task diff refreshing `синхронизировано` only.
- `both_moved`, `event_missing` → a question; no proposal.
- `closed_with_future_event` → delete preview plus a task diff removing the
  `Событие:` line.
- `unlinked` → task diff adding the `Событие:` line.

Never change `Due:`; if the new time falls after `Due:`, ask separately.
Each pair follows the existing joint confirmation. The user may confirm all
items or selected numbers. If the calendar read failed, say so and render no
items; render `- Нет.` when the list is empty. The script is read-only.

The script converts event times to the calendar timezone taken from the
`read_events` response before comparing them; each returned item also carries
the task's `due` field for the after-`Due:` check; note that event IDs can
change after a full calendar re-sync, which surfaces as `event_missing` and is
only a question, not a definite discrepancy.

## Recommendations and validation

Under `## Рекомендации`, use `resources/calendar-context.md` to analyze the past 30 days and next 14 days and suggest grounded actions for today. Keep this fourth section even if context is unavailable and state the limitation.

Apply the active rules in `<hub>/ai/workflow-context.md` here, including any productive-window rule. A productive window is a recommendation, not a schedule: name the specific task that should take that window and why, cite its canonical source, and never present the window as an applied calendar change. The day plan itself proposes no calendar blocks; a schedule is created only through the editing path below or `hub-calendar`.

### Weight

Rank candidate work for a productive window by stated weight only, and name which of these three bases was used for every ranked item:

1. an exact `Запланировано:` range or another stated duration in the canonical record;
2. otherwise the number of `## Scope` or `## Done criteria` items in that record;
3. otherwise unknown.

Never invent an estimate, never infer weight from a title, and never compare an item whose basis is unknown against a measured one without saying so.

### Swap suggestion

When the window is already occupied, first state what occupies it and how much of it remains free. Then emit at most one swap suggestion per plan, and only when all of these hold:

- the heaviest candidate does not fit the remaining free time;
- the event to be shortened maps to one registered project in scope by the `категория/проект/задача` convention and its canonical task record;
- shortening it frees enough contiguous time for the candidate.

Never suggest shortening or moving an event that involves other people, such as a meeting or a call, and never one for sleep, meals, travel, or personal care. A long project work block may be shortened, but the suggestion must name the exact range to reassign and both canonical sources.

Render the suggestion as a suggestion: state explicitly that nothing is changed and that a calendar preview under `hub-calendar` follows only after the user asks for it. Emit no proposal envelope and no calendar preview inside the day plan itself.

Before sending the result, pass the complete draft on stdin to `scripts/validate-day-plan-output.py`. Send only after it exits successfully; otherwise rewrite and validate again. A cache-write failure never permits omitting `## Рекомендации`.
