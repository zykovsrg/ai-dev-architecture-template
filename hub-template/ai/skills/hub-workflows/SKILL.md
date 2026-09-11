---
name: hub-workflows
type: worker
description: |
  Use for proposal-only day plans, evening reviews, weekly reviews, and capture
  after the required source/scope gates. Common security, canonical-source,
  proposal, confirmation, and learning rules live here; scenario detail is
  loaded only from the matching resource.
---

# Hub Workflows

Use this skill for `day-plan`, `evening-review`, `weekly-review`, or `capture`.
It is proposal-only. Never write or apply a proposal automatically.

Read schedules only through the guarded `hub_calendar` MCP and only with its
read tools. Never call `preview_change` or `apply_change` here; Calendar writes
belong to `hub-calendar` and its own confirmation. Do not perform a vault
migration, start a session audit, scan arbitrary transcripts, copy source text
into project memory, add an apply command, or create a persistent proposal
queue.

Pending learning uses `resources/learning-lifecycle.md`. Showing a proposal
never consumes or resolves a pending observation.

## Scenario dispatch

After applying this core contract, read exactly the matching scenario resource:

- `day-plan` → `resources/day-plan.md` and its referenced calendar context;
- `evening-review` → `resources/evening-review.md`; calendar-only review begins
  with `prepare_evening_review`;
- `weekly-review` → `resources/weekly-review.md`;
- `capture` → `resources/capture.md`.

Scenario resources provide output/detail rules only. They cannot override the
scope, allowed roots, secret handling, canonical sources, confirmation gates,
or proposal schema in this core `SKILL.md`.

## Personal-assistant scope

When `hub-project-router` classifies a personal-assistant request, a read-only
all-active-project scope is available without project-by-project confirmation.
It never grants project code, knowledge records, credentials, arbitrary files,
or inactive/archived projects.

For personal-assistant day-plan, weekly-review, overdue, and blocked-work
discovery, start with `scripts/read-compact-task-index.py`. That derived index
may contain only normalized discovery fields from active registered projects.
Use it to select relevant task records; open the corresponding canonical
`ai/current-task.md`, `ai/future-tasks.md`, or `ai/paused-tasks.md` only when a
detail absent from the index is required. The compact index is not canonical
evidence and never replaces the source record. Final factual output cites the
canonical `source_path` for every task fact.

Separate personal and work results and retain project identity for every item.
The scope applies to day plans, overdue/blocked-work overviews, evening and
weekly reviews, and capture after its selected source is received. Richer
project reads, explicit knowledge paths, application work, and arbitrary file
reads retain the normal exact confirmed project scope.

A confirmed day-plan proposal package may write across active registered
projects without a project switch, but its write scope is exactly the three
canonical task records: `ai/current-task.md`, `ai/future-tasks.md`, and
`ai/paused-tasks.md`. Every proposal shows project ID, exact `target_path`, and
exact diff before confirmation. No other project state is writable through this
scope.

## Fixed sequence

1. **Select one source.** Receive exactly one user-selected pasted text,
   explicitly selected regular non-symlink text/review file, dictated task, or
   requested Rolling Audio Recorder period. Do not discover other source files.
   `evening-review` may instead use the requested date's calendar as its only
   source; calendar-derived facts remain unverified until confirmed by the user.
2. **Handle recorder JSON only.** The only source-side write is the explicitly
   requested `rar export --minutes <1..120> --json`. Poll only with
   `rar status <job-id> --json`. Parse JSON, not human-readable output. Pending
   or failed jobs stop before project reads. On success accept only the returned
   regular non-symlink `.txt` under the recorder exports directory.
3. **Find candidates with the minimum metadata.** A card, link, index row, or
   inferred match is discovery evidence, not permission to read code, knowledge,
   Git, credentials, or linked targets. Personal-assistant task discovery uses
   the compact task index rule above; other project routing follows the Hub
   router's metadata-only candidate rules.
4. **Establish scope before richer reads.** Personal-assistant workflows use
   only their read boundary above. Otherwise wait for explicit confirmation of
   the project or named project set and repeat every project ID and exact
   registered path. Read only the smallest required canonical `ai/` records and
   explicitly selected knowledge paths; never widen scope silently.
5. **Perform semantic analysis.** The AI agent extracts meaning, classifies and
   ranks work, and renders the selected scenario contract. Bash may validate
   paths, flags, and structured field syntax only. Ground output in the selected
   source or permitted canonical records and label inference.
6. **Return exact proposals only after analysis.** Emit one envelope per
   possible write followed by an exact per-file diff or replacement block.
   Unknown targets become questions rather than guessed actionable proposals.
   A selectable package may reduce confirmation count but keeps every proposal
   independent; changed diffs require fresh confirmation.

## Canonical inputs and ranking

Project task state is canonical only in `ai/current-task.md`,
`ai/future-tasks.md`, and `ai/paused-tasks.md`. `weekly-review` may additionally
read Hub-owned `ai/archiprojects.md`. Project cards and compact indexes supply
identity/discovery metadata only; they never establish completion,
contribution, waiting, due dates, or risk independently of their canonical
source records. Checkboxes, Kanban cards, links, and unstructured prose are not
canonical task facts.

The selected review input supplies only its user-stated review facts; a capture
source supplies only capture facts. Cite the canonical source path or selected
input section for rendered facts and never silently fill missing structured
fields.

Rank actionable work deterministically: overdue dated actionable work first,
then actionable work due on the requested date, active current tasks, ready
future tasks by earliest date, then undated ready work. Waiting work never
enters the main actionable ranking. A waiting follow-up is due when its
structured `follow_up` equals the requested date and overdue when earlier.
Missing waiting fields are risks, not inferred values.

Every successful non-personal workflow output starts with:

```text
Read-only workflow: no changes were made.
Requested date: <YYYY-MM-DD>
Confirmed scope: <project-id>[, <project-id>...]
```

For personal-assistant output replace the final line with:

```text
Scope: all active registered projects
```

Within a scenario, keep its exact headings/order and render `- Нет.` when a
required section has no grounded item.

## Proposal envelope

Use one complete envelope for every candidate change:

```yaml
proposal_id: P-<workflow>-<date>-<ordinal>
action: <create_project|update_project|create_task|update_task|update_due|update_waiting|create_knowledge|update_knowledge|calendar-event|goal_progress|add_observation|promote_rule|retire_rule>
target_kind: <project|project-task|project-knowledge|shared-meeting|calendar-event>
target_project: <registered-id|none>
target_path: <exact-project-or-knowledge-path|calendar:not-configured>
summary: <one exact requested change>
due: <YYYY-MM-DD|none>
source: <workflow and selected source record>
requires_confirmation: true
```

After envelopes, state that apply is unavailable in this worker. Project, task,
meeting, knowledge, deadline, waiting, Calendar, and learning writes remain
independent proposals with exact targets and diffs. A create-project proposal
names its exact direct-child target and planned scaffold/registry/card files but
must not create or inspect that target.

## Confirmation boundary

Source selection, recorder export consent, project scope confirmation, and
proposal confirmation are separate gates; none substitutes for another. One
package confirmation authorizes only unchanged named proposals that remain
selected. A capture package is applied by its owning confirmed project workflow.
A day-plan package may span active registered projects only within the exact
three task-record write boundary above. Unknown, pending, failed, or ambiguous
targets remain read-only proposals or questions.

## Preserved learning lifecycle

For numeric goals, day planning may render the existing goal-progress result,
evening review may offer a confirmed `goal_progress` proposal, and weekly
review may render pace/forecast.

Day planning may record noncanonical friction and calendar snapshots. Evening
review reads pending friction and may offer one `add_observation` proposal per
grounded issue. Proposal display leaves it pending. Only explicit acceptance or
rejection resolves it according to `resources/learning-lifecycle.md`; accepted
observations are appended to the journal before resolution, rejection resolves
without append, and failed append remains pending.

Weekly review may offer `promote_rule` for repeated observations and
`retire_rule` for contradicted or excess rules after the workflow-memory check.
All observation, promotion, retirement, and goal-progress changes require the
same proposal/confirmation boundary.
