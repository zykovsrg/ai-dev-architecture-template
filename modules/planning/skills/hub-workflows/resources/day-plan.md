# day-plan

This resource defines only the `day-plan` scenario. The core `SKILL.md` remains authoritative for scope, security, canonical-source rules, proposal envelopes, write policy, and learning lifecycle. Nothing here widens those permissions.

When the request names an archiproject group, resolve it via
`scripts/archiprojects.py tree --hub <hub>` and pass `--group <group-id>` to
`scripts/read-compact-task-index.py`, same as the core `SKILL.md` group
filter; report an unknown group instead of guessing. This only narrows task
discovery to the group's member projects — it never substitutes for project
routing elsewhere.

Read `resources/calendar-context.md` on every run. Day planning may maintain that local noncanonical calendar context buffer; calendar events and project task records follow the normal write policy.

A successful `day-plan` renders these headings in this exact order:

1. `## Текущий календарь`
2. `## Синхронизация`
3. `## Просроченные задачи`

Do not add task-outside-calendar or recommendation sections. Overdue tasks are
always the final section; calendar synchronization does not replace their check.
Report actual writes truthfully: a cache-only write is not a task write, and a
successful task synchronization must not be described as "tasks unchanged".

## Before composing the plan

The user first arranges approximate work in Calendar. Every requested day plan
then performs the following steps, without a scheduled automation or reminder:

1. Read allowed Calendar metadata, today's events and the complete context window.
2. Discover canonical tasks through the compact task index and run synchronization
   using the complete fresh calendar response as described below.
3. Apply unambiguous task-time changes using Calendar as the source of truth.
   Validate task records, then reload the compact index and changed canonical
   records before ranking work or composing any task section.
4. Render the three sections from the refreshed state, with overdue tasks last.
5. Refine the day with the user. After accepted edits, verify only affected dates
   and task records and refresh their cache buckets; do not repeat full-window
   synchronization in the same run.

Partial Calendar access must not produce inferred free time or task mutations.
On a read or write failure, say precisely what remains unsynchronized and use
only verified state. Do not claim the plan uses synchronized data after failure.

## Calendar rendering

Under `## Текущий календарь`, first call `list_calendar_metadata`. Only after a successful response call `read_events` with exactly the returned calendar IDs and the calendar timezone. Render each timed event separately, in start order, as `- <HH:MM>–<HH:MM> — <title>`. Render each all-day event separately as `- весь день — <title>`. Include the calendar name only when needed to disambiguate. Keep event titles verbatim: do not shorten, translate, group, or paraphrase them.

Never call `read_events` before successful metadata. If the MCP is unreachable, permission is missing, or the allowlist is empty, state which condition occurred rather than inventing an empty schedule. Do not report an empty allowlist without a successful metadata response and never claim a free day you could not read. On `CALENDAR_NOT_ALLOWED`, read the local allowlist file and retry with exactly its IDs; report an empty allowlist only when that file is confirmed empty.

For each successful `read_events` response, inspect `availability_complete` and `unavailable_calendar_ids`. If coverage is incomplete, render returned events and name unavailable calendar IDs; never interpret missing events as free time. If a calendar-context window read is incomplete, state that synchronization is incomplete and do not use partial data.

When the requested date's read is complete, pipe one `HH:MM|HH:MM|<title>|<calendar>` line per event, in start-time order, to `bash scripts/snapshot-calendar.sh --hub <hub> --at <date>-<HHMM>`. This morning snapshot is the plan that the evening review compares against; a snapshot failure is reported and does not block the day plan.

## Task sections

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

Preserve the exact user-stated task title unless the user explicitly replaces it. Each proposal keeps its own exact target and diff. When a task carries a schedule, write its calendar event together with the task under `hub-calendar`. A selectable package may span active projects, but every proposal retains its own project ID, `target_path`, and diff.

For a direct, unambiguous user statement about one canonical task, apply
exactly one `update_task`, `update_due`, or `update_waiting` change to the
canonical record at once, plus the calendar change only when the task schedule
changes, and report the project ID, target path, and diff. If the task
reference is ambiguous, change nothing and ask which task is meant.

For a new or changed action with relative and explicit dates, resolve the date
in the calendar timezone. Preserve an explicit interval unchanged. A date-only
statement uses the first 30-minute free interval on that date; never move an
existing event. Put the result in `Запланировано: YYYY-MM-DD HH:MM-HH:MM` in
the task record and create the matching calendar event without asking. A past date does not infer completion.

Do not guess project ownership. If one active registered project cannot be identified, ask which project owns the statement and write no task or event. If the canonical record already contains the statement, say so rather than emitting an empty diff.

## Sync section

Run sync only when all calendar-context window reads are complete (`availability_complete: true` and no `unavailable_calendar_ids`). Otherwise report that synchronization is incomplete and render no discrepancy items from partial data.

Before composing the plan, pipe the guarded `read_events` response for the
calendar-context window [D-30, D+31) to
`python3 scripts/calendar_task_sync.py --hub <hub> --now "<YYYY-MM-DD HH:MM>"`.
Reuse a complete window response already fetched in this run; do not read the
same window again solely for sync. After task or calendar edits, re-read only
the affected dates to verify changed events and refresh their calendar-context
buckets. Do not repeat the full-window sync after those edits in the same run;
the next day-plan run performs the normal sync.
Report results under `## Синхронизация`: one numbered item per discrepancy
in Russian, stating what moved and from/to times. The output section does not
delay synchronization until after composing the plan:

- `calendar_moved` → `update_task` proposal: set `Запланировано:` to the event
  time and refresh `синхронизировано`.
- `task_moved` → task diff restoring `Запланировано:` to the linked Calendar
  event time and refreshing `синхронизировано`; do not move Calendar implicitly.
- `stale_sync` → task diff refreshing `синхронизировано` only.
- `both_moved` → use Calendar only when the linked event and its occurrence
  are unambiguous; otherwise ask one question and make no mutation.
- `event_missing` → a question; no proposal.
- `closed_with_future_event` → delete preview plus a task diff removing the
  `Событие:` line.
- `unlinked` → task diff adding the `Событие:` line.

Never change `Due:` through synchronization. An unambiguous schedule change
may be applied even after `Due:`; report the missed deadline and ask separately
about changing it. Keep the task in the overdue section until the user changes
its deadline or confirms completion.
Apply unambiguous `calendar_moved`, `task_moved`, `both_moved`, `stale_sync`, and `unlinked` items
directly and list them as done. A `closed_with_future_event` item deletes an
event and waits for an explicit yes; the user may answer for all such items or
selected numbers. If the calendar read failed, say so and render no
items; render `- Нет.` when the list is empty. The script is read-only.

The script converts event times to the calendar timezone taken from the
`read_events` response before comparing them; each returned item also carries
the task's `due` field for the after-`Due:` check; note that event IDs can
change after a full calendar re-sync, which surfaces as `event_missing` and is
only a question, not a definite discrepancy.

## Joint planning and validation

Use the past 30 days and next 14 days from `resources/calendar-context.md`,
canonical deadlines, learned rules from `<hub>/ai/workflow-context.md`, and
available goal-progress results to support joint planning. These inputs stay
internal to analysis; they create no recommendation section, calendar block,
or task change by themselves. Historical events do not prove completion.
A learned rule naming a removed output section does not restore that section.

When discussing workload with the user, use only recorded durations, scope or
done-criteria counts, or explicitly unknown effort. Never invent estimates.
Do not silently move or shorten other people's meetings, sleep, meals, travel
or personal care. Apply user-requested changes through the existing editing
path and verify their exact task/calendar targets afterwards.

Discovery warnings, access limitations and required scheduling decisions belong
under `## Синхронизация`, with their project and canonical source where known.
Keep that section even if synchronization found no discrepancies (`- Нет.`).

Before sending the result, pass the complete draft on stdin to
`scripts/validate-day-plan-output.py`. Send only after it exits successfully;
otherwise rewrite and validate again. Cache failures do not change the required
three-section format.
