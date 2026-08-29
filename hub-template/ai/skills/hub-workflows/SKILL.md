---
name: hub-workflows
type: worker
description: |
  Use for proposal-only day plans, evening reviews, weekly reviews, and capture
  from one user-selected text, transcript, dictated task, review file, or
  Rolling Audio Recorder period. Performs semantic analysis after scope
  confirmation and never applies a proposal automatically.
---

# Hub Workflows

Use this skill for `day-plan`, `evening-review`, `weekly-review`, or `capture`.
It is proposal-only. Never write or apply a proposal automatically.

Do not run Calendar MCP, perform a vault migration, start a session audit, scan
for arbitrary transcripts, or copy source text into project memory. Do not add
an apply command or a persistent proposal queue.

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
   other files. Do not read project data yet.
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

### Day plan format

`day-plan` renders these headings in this exact order:

1. `## Сегодня: контекст`
2. `## Три главных действия`
3. `## Остальные действия`
4. `## Ожидания и follow-up`
5. `## Риски и сроки`
6. `## Календарь`
7. `## Нужны решения`

Under `## Три главных действия`, render at most three ranked executable results,
not vague themes or waiting items. Number them `1.` through `3.` and use
`<result> — <project-id>; срок: <YYYY-MM-DD|нет>; источник: <canonical-path>`.
Put remaining actionable work under `## Остальные действия`. Keep waiting and
due or overdue follow-ups together under `## Ожидания и follow-up`; put unknown
states, missing waiting fields, blockers, and dated risks under `## Риски и
сроки`. Under `## Календарь`, always render exactly `Недоступен в этом этапе:
Calendar не подключён.` Ranking is read-only and never becomes a proposal by
itself.

### Evening review format

`evening-review` renders these headings in this exact order:

1. `## Сделано`
2. `## Перенос`
3. `## Ожидания`
4. `## Follow-ups`
5. `## Завтрашний Calendar`
6. `## Три главных действия завтра`
7. `## Подтвердить`

Fill `## Сделано` only from `--review-input` section `## Done`, `## Перенос`
only from `## Carry over`, and the user-stated part of `## Ожидания` only from
`## Waiting`; append separately cited canonical waiting records from confirmed
scope. Derive `## Follow-ups` and tomorrow's at-most-three ranked executable
results only from structured canonical fields. Under `## Завтрашний Calendar`,
always render exactly `Недоступен в этом этапе: Calendar не подключён.` A stated
completion, carry-over, waiting, or due-date change is a user fact in this
report, not a canonical change; any possible write remains an independent
proposal listed for confirmation under `## Подтвердить`.

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
