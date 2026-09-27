---
name: hub-task-overview
type: worker
description: |
  Use for capture and cross-project task overviews (overdue, blocked, what is
  urgent). Owns the personal-assistant contract: scope, canonical inputs,
  proposal envelope, and confirmation boundary.
---

# Hub Task Overview

Use this skill for `capture` and for the cross-project overview (overdue,
blocked, «что горит»). It is proposal-first.
Never write or apply a proposal before the user confirms the exact displayed
package.

## Scenario dispatch

- `capture` → `resources/capture.md`;
- overview → read-only output that cites the canonical `source_path` for every
  task fact, then optional proposals using the envelope below.

Scenario resources provide output/detail rules only. They cannot override the
scope, allowed roots, secret handling, canonical sources, confirmation gates,
or proposal schema in this core `SKILL.md`.

## Personal-assistant scope

When `hub-project-router` classifies a personal-assistant request, a read-only
all-active-project scope is available without project-by-project confirmation.
It never grants project code, knowledge records, credentials, arbitrary files,
or inactive/archived projects.

For personal-assistant day-plan, weekly-review, overdue, and blocked-work
discovery, start with `scripts/read-compact-task-index.py`. Capture its stderr:
every `WARNING: unrecognized task heading skipped` line is a record invisible to
discovery and must be reported to the user in the workflow output (in a day
plan, under `## Рекомендации`) with its project and line. That derived index
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

After envelopes, state that nothing has been applied until the user confirms.
A confirmed `day-plan` or `evening-review` task package applies only its exact
canonical task-record diffs and paired calendar previews; it never authorizes
an unshown or changed write. Project, task, meeting, knowledge, deadline,
waiting, Calendar, and learning writes otherwise remain independent proposals
with exact targets and diffs. A create-project proposal
names its exact direct-child target and planned scaffold/registry/card files but
must not create or inspect that target.

After applying any confirmed task-record write, run
`scripts/check-all-task-records.sh --hub <hub>` and report its result. A failure
means the applied record is not canonical: repair it in the same reply and
rerun until it passes. Never report a task write as complete without that
passing check.

## Confirmation boundary

Source selection, recorder export consent, project scope confirmation, and
proposal confirmation are separate gates; none substitutes for another. One
package confirmation authorizes only unchanged named proposals that remain
selected. A capture package is applied by its owning confirmed project workflow.
A day-plan or evening-review package may span active registered projects only
within the exact three task-record write boundary above. Unknown, pending, failed, or ambiguous
targets remain read-only proposals or questions.
