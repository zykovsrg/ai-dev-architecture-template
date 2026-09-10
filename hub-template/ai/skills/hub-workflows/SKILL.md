---
name: hub-workflows
type: worker
description: |
  Use for proposal-only day plans, evening reviews, weekly reviews, and capture
  from one user-selected text, transcript, dictated task, review file, or
  Rolling Audio Recorder period. An evening review may instead read the
  requested date's calendar, link its events to projects, and propose task
  status updates. Performs semantic analysis after scope
  confirmation and never applies a proposal automatically.
---

# Hub Workflows

Use this skill for `day-plan`, `evening-review`, `weekly-review`, or `capture`.
It is proposal-only. Never write or apply a proposal automatically. Pending
learning observations use the separate lifecycle in
`resources/learning-lifecycle.md`: showing a proposal never consumes it.

Read the schedule only through the guarded `hub_calendar` MCP, and only with
its read tools. Never call `preview_change` or `apply_change` here: a calendar
change belongs to `hub-calendar` and its own confirmation. Do not perform a
vault migration, start a session audit, scan for arbitrary transcripts, or copy
source text into project memory. Do not add an apply command or a persistent
proposal queue.

Day planning may maintain the local calendar context buffer described in
`resources/calendar-context.md`. Read that resource on every day-plan run.
This is an explicit noncanonical cache exception to proposal-only writes;
calendar events and project records still require their usual confirmation.

## Personal-assistant scope

When `hub-project-router` classifies a personal-assistant request, this skill
may read `ai/current-task.md`, `ai/future-tasks.md`, and `ai/paused-tasks.md`
from all active registered projects without project-by-project confirmation.
This is a read-only all-active-project scope, not a general project grant: do
not read project code, knowledge records, credentials, arbitrary files, or
inactive/archived projects. Separate personal and work results, and cite the
project ID plus canonical path for each factual item.

The personal-assistant scope applies to day plans, overdue or blocked-work
overviews, evening or weekly reviews, and capture after its selected source is
received. Richer project reads, explicit knowledge paths, and any project-local
implementation work retain the normal exact confirmed scope.

## Fixed sequence

1. **Select one source.** Receive exactly one user-selected source and name its
   type and purpose. Allowed sources are pasted text, one explicitly selected
   regular non-symlink text file, a dictated task, one explicitly selected
   review file, or a requested Rolling Audio Recorder period. Do not discover
   other files. Do not read project data yet. `evening-review` may run without
   a selected source: in that case the requested date's calendar is the only
   source, and every fact it yields stays unverified until the user confirms
   it.
2. **Handle recorder JSON only.** For a requested period, the only allowed
   source-side write is the user's requested
   `rar export --minutes <1..120> --json`. Poll only with
   `rar status <job-id> --json`. Parse the returned JSON; never infer job state
   from human-readable output. If state is pending, show the job ID and stop.
   If state is failed, show the recorder error and stop. In either case, do not
   read project data. On success, accept only the explicitly returned regular,
   non-symlink `.txt` transcript below the recorder exports directory.
3. **Find candidates from metadata.** Run a metadata-only candidate search.
   Show at most the useful candidate IDs, their exact registered paths, the
   evidence for each match, and the intended purpose of any later read. A card,
   link, or inferred match is not permission to read project memory, knowledge,
   code, Git, or linked targets.
4. **Confirm scope before full reads.** For a personal-assistant request, use
   the all-active-project scope above and read only its three canonical task
   records. Otherwise wait for an explicit confirmation of a confirmed project
   or named confirmed set. Repeat every project ID and exact registered path.
   Only then may you read the smallest required canonical `ai/` records for
   that scope and explicitly selected project-local `knowledge/` paths. Never
   widen the confirmed set silently.
5. **Perform semantic analysis.** The AI agent, not the Bash guardrail, extracts
   meaning, classifies records, ranks work, and renders the deterministic output
   below. Bash may validate paths, flags, and structured field syntax only. For
   `capture`, first render separate sections for source facts, stated decisions,
   action candidates, likely projects, knowledge candidates, dates, waiting or
   follow-up, and ambiguities. Ground every item in the selected source or
   confirmed canonical records. Label inference and never treat it as approval.
6. **Return exact proposals only after analysis.** Emit one proposal envelope
   per possible write, followed by one exact per-file diff or replacement
   block. Keep proposals independent; if an exact allowed target file is not
   known, ask a question instead of guessing or emitting an actionable
   proposal. For one capture result, present the envelopes as one selectable
   proposal package. A package confirmation may authorize only unchanged named
   proposals that remain selected; the user may exclude individual proposal
   IDs. Every proposal retains its exact target and diff, and any changed diff
   needs new confirmation. Outside that package, show a fresh exact diff and
   wait for named proposal confirmation.

## Capture rules

- Read the first non-empty source line as the declared kind. Reject any kind
  other than `Kind: meeting` or `Kind: task`.
- For `Kind: meeting`, the first proposal is exactly one canonical
  meeting-record proposal. Task, project, knowledge, deadline, and waiting
  proposals refer to that meeting record but remain independent.
- For `Kind: task`, emit no meeting-record proposal. Allow only a grounded task
  or knowledge proposal.
- If no registered project fits, keep the unknown target as an
  `action: create_project` proposal. Do not create, register, or inspect a new
  project automatically.

## Workflow outputs

### Canonical inputs and ranking

For task and project semantics, read only the confirmed scope's canonical
`ai/current-task.md`, `ai/future-tasks.md`, and `ai/paused-tasks.md` records.
`weekly-review` may also read the hub-owned canonical `ai/archiprojects.md`.
Project cards supply identity and registered-path metadata only; they never
supply task state, completion, contribution, due dates, waiting, or risk.
Checkboxes, Kanban cards, links, and unstructured project prose are not
canonical facts. The selected `--review-input` supplies only the user-stated
evening facts in its named sections. The selected capture source supplies only
capture facts. Cite the canonical relative path or selected input section for
every rendered fact; do not silently combine records or fill missing fields.

Rank actionable work deterministically: overdue dated actionable work first,
then actionable work due on the requested date, active current tasks, ready
future tasks by earliest date, and undated ready work. Waiting work never enters
the main ranked list. A waiting follow-up is due when `follow_up` equals the
requested date and overdue when it is earlier. Missing structured waiting
fields are risks, not inferred values.

Every successful non-personal workflow output starts with these exact lines:

```text
Read-only workflow: no changes were made.
Requested date: <YYYY-MM-DD>
Confirmed scope: <project-id>[, <project-id>...]
```

For a personal-assistant result, replace the last line with:

```text
Scope: all active registered projects
```

Within every section, keep canonical ranking order and render `- Нет.` when the
section has no grounded item. Do not rename, merge, repeat, or reorder the
headings defined below.

For a day-plan run that writes its local buffer, replace the no-changes line
with: `Обновлён локальный контекст; календарь и задачи не изменены.`

### Day plan format

`day-plan` renders these headings in this exact order:

1. `## Текущий календарь`
2. `## Конфликты`
3. `## Задачи вне календаря`
4. `## Просроченные задачи`
5. `## Предлагаемый календарь`
6. `## Рекомендации`

Under `## Текущий календарь`, render the schedule for the requested date:
first call `list_calendar_metadata`. Use exactly the IDs from its successful
response in `read_events`, using the calendar timezone, and render one line per event as
`- <HH:MM>–<HH:MM> — <title>` in start order. Render each event as a separate
bullet; include the calendar name in parentheses only when it helps distinguish
events. Never call `read_events` before a successful `list_calendar_metadata`
response. State plainly that the day holds no event when it holds none. If the
MCP is unreachable, the permission is missing, or the allowlist is empty, say
which of those it is instead of rendering an empty schedule; do not report an
empty allowlist without a successful metadata response and never claim a free
day you could not read. Render the calendar event title verbatim. Do not shorten,
translate, group, or paraphrase it.

Under `## Конфликты`, list only grounded conflicts: overlapping calendar
events, or an actionable task with an exact `Запланировано:` range that overlaps
a calendar event or another exact task range. Cite both records. Do not infer a
conflict from a task without an exact time range; report `- Нет.` when no
grounded conflict exists.

Under `## Задачи вне календаря`, render ranked actionable tasks from the
confirmed scope that have neither an exact `Запланировано:` range on the
requested date nor a grounded calendar match. Exclude overdue tasks from this
section. Use `<result> — <project-id>; срок: <YYYY-MM-DD|нет>; источник:
<canonical-path>`.

Under `## Просроченные задачи`, render every actionable task whose due date is
before the requested date as `<exact canonical task title> — <project-id>;
срок: <YYYY-MM-DD>; просрочено: <N> дн.; источник: <canonical-path>`.
Use the exact canonical task title, never a summary, translation, or generated
label. Do not repeat a task in another day-plan section.

Under `## Предлагаемый календарь`, render one chronological day view that keeps
each current calendar event and adds proposed blocks for the highest-ranked
unscheduled or overdue tasks where a free window is available. Render each
entry, kept or proposed, as a separate bullet: `- <HH:MM>–<HH:MM> — <title>;
статус: <сохраняется|предлагается>;
основание: <calendar|canonical-path>; duration: stated|estimate`. A proposed
duration must use a stated duration from its canonical task record when one is
available; otherwise mark it `estimate`. Apply learned rules and active numeric
goal progress as planning constraints, but do not add a separate section for
them. If a task cannot fit, name it at the end of this section as `Не вошло`;
do not invent a time or remove a current event. The proposed calendar is
read-only and never becomes a Calendar change without its separate preview and
confirmation. For a retained event, use its calendar title verbatim. For a new
block, use the exact canonical task title; do not create a summary or a new
phrase for either kind of entry.

When the user explicitly states a new action or reminder for today while
planning, turn it into a `create_task` or `update_task` proposal for the
confirmed project that owns the action, as well as any appropriate proposed
calendar block. Preserve the exact user-stated task title unless the user
explicitly supplies a replacement. A day-plan project-task proposal has its
own exact target path and diff, and remains independently selectable from its
calendar proposal. Do not guess a project: if the action cannot be grounded in
one confirmed project, ask which confirmed project owns it and make no task or
calendar proposal until the user answers.

Under `## Рекомендации`, follow `resources/calendar-context.md`: analyze
the past 30 days and next 14 days to suggest grounded actions for today.
Keep this sixth section even when context is missing; explain the limitation.

### Evening review format


`evening-review` renders these headings in this exact order:

1. `## Сегодняшний календарь`
2. `## События и проекты`
3. `## Сделано`
4. `## Перенос`
5. `## Ожидания`
6. `## Follow-ups`
7. `## Завтрашний Calendar`
8. `## Три главных действия завтра`
9. `## Подтвердить`

Under `## Сегодняшний календарь`, render the requested date's schedule by the
same rule as the day plan, in start order. Under `## События и проекты`, map
each rendered event to at most one registered project of the confirmed scope,
using only the event title, the `категория/проект/задача` naming convention,
and canonical task records as evidence. Render one line per event as
`<HH:MM> <title> → <project-id|нет совпадения>; основание: <evidence>;
уверенность: <высокая|низкая>`. A calendar match is an inference, never a
canonical fact: it never proves a task was completed, never widens the
confirmed scope, and never authorizes a read outside it. Leave an event
unmatched rather than guessing between two projects.

Fill `## Сделано` from `--review-input` section `## Done`, `## Перенос`
only from `## Carry over`, and the user-stated part of `## Ожидания` only from
`## Waiting`; append separately cited canonical waiting records from confirmed
scope. When no `--review-input` was selected, fill `## Сделано` instead from
past events of the requested date that matched a project above, mark every such
line `предположение из календаря` with its event and project, and state plainly
that the section was not confirmed by the user. Never render a
calendar-derived line as a stated completion. Derive `## Follow-ups` and tomorrow's at-most-three ranked executable
results only from structured canonical fields. Under `## Завтрашний Calendar`,
render tomorrow's schedule by the same rule as the day plan. A stated
completion, carry-over, waiting, or due-date change is a user fact in this
report, not a canonical change; any possible write remains an independent
proposal listed for confirmation under `## Подтвердить`. Every matched event
and every calendar-derived completion line may produce at most one
`update_task` proposal for the matched project's canonical task record, each
with its own exact target path and diff. Emit no proposal for an unmatched
event, a low-confidence match, or a project outside the confirmed scope.

### Weekly review format

`weekly-review` renders these headings and blocks in this exact order:

1. `## Архипроекты`
2. one `### <archiproject-id> — <name>` block per scoped primary archiproject;
3. an optional `#### Детали проектов` block immediately after its owning
   archiproject block;
4. `## Три результата недели`;
5. `## Нужны решения`.

Each archiproject block uses this fixed field order: `- Цель:`, `- Вклад
основного проекта:`, `- Срок/прогноз:`, `- Ожидания и follow-up:`, then `-
Риск:`. Only canonical primary-archiproject membership counts; related links do
not imply contribution. Project detail appears only for a dated risk, blocker,
or waiting record. Make that detail readable as `- <project-id> — <risk,
blocker, or waiting>; дата: <YYYY-MM-DD>; источник: <canonical-path>` and omit
the detail heading when no such record exists.

Under `## Три результата недели`, render exactly three proposed weekly results
as numbered executable outcomes grounded in canonical records. If a grounded
result is unavailable, keep its numbered slot and write `Недостаточно
канонических данных для результата.` rather than inventing one. If
`ai/archiprojects.md` is missing or contains no scoped archiproject, state that
fact under `## Архипроекты`, omit invented archiproject blocks, and still show
safe project-level risks before the three result slots.

`capture` first reports source type, decisions, actions, project candidates,
knowledge candidates, dates, waiting, and ambiguity. Then it reports proposal
envelopes in source order, subject to the meeting/task rules above.

## Proposal envelope

Use one complete envelope for every candidate change:

```yaml
proposal_id: P-<workflow>-<date>-<ordinal>
action: <create_project|update_project|create_task|update_task|update_due|update_waiting|create_knowledge|update_knowledge|calendar-event>
target_kind: <project|project-task|project-knowledge|shared-meeting|calendar-event>
target_project: <registered-id|none>
target_path: <exact-project-or-knowledge-path|calendar:not-configured>
summary: <one exact requested change>
due: <YYYY-MM-DD|none>
source: <workflow and selected source record>
requires_confirmation: true
```

After the envelopes, state that apply is unavailable. A possible project,
task, meeting, knowledge, deadline, waiting, or Calendar write remains an
independent proposal with its own exact diff and `target_path`. A capture may
render all independent envelopes as one selectable proposal package; this
reduces confirmation count without combining their writes. A create-project
proposal must name the exact proposed direct-child path and list each planned
scaffold, registry, and card file, but must not create or inspect that target.

## Confirmation boundary

Source selection, recorder export consent, scope confirmation, and proposal
confirmation are separate gates. None substitutes for another. A one selectable
proposal package can be applied only by its owning confirmed project workflow
after one confirmation that names the unchanged named proposals still selected.
Unknown, pending, failed, or ambiguous targets remain read-only proposals or
questions.

## Preserved learning lifecycle

For every active numeric goal, `day-plan` renders the verbatim result of
`count-goal-progress.sh`; evening review asks for a stated amount and offers a
separate confirmed `goal_progress` proposal. `weekly-review` renders each
goal's verbatim pace and forecast.

Day plan renders every learned rule from `ai/workflow-context.md`, snapshots
the requested calendar day with `snapshot-calendar.sh`, and records friction in
the day's non-canonical cache. Evening review snapshots the same day, compares
its complete snapshot history, reads unconsumed friction, and proposes one
`add_observation` per grounded issue. It then marks that friction cache
consumed. Snapshot and friction caches are pruned after 14 days.

Weekly review reads the observation journal, groups repeated friction or
calendar drift, and proposes `promote_rule` after three repeats or two in one
week. It proposes `retire_rule` for a contradicted or excess rule. Before those
proposals it runs `check-workflow-memory.sh`; failure blocks only rule changes.
All observation, promotion, and retirement proposals require confirmation.
