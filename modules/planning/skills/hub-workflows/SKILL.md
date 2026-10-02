---
name: hub-workflows
type: worker
description: |
  Use for day plans, evening reviews, and weekly reviews after
  the required source/scope gates. The personal-assistant contract lives in
  `hub-task-overview`; learning rules live here; scenario detail is loaded only
  from the matching resource.
---

# Hub Workflows

Use this skill for `day-plan`, `evening-review`, or `weekly-review`.
Writes follow the Write Confirmation Policy in `ai/architecture.md`. A change
the user states (task done, moved, new action, goal amount) is applied at once
and reported; only deletions wait for an explicit yes. Blocks the agent itself
suggests in a plan are suggestions; once the user accepts them they are applied
without another confirmation step.

Module rules: `ai/rules/planning.md`.

Read schedules only through the guarded `hub_calendar` MCP and only with its
read tools. Never call `preview_change` or `apply_change` here; Calendar writes
go through `hub-calendar`. Do not perform a vault
migration, start a session audit, scan arbitrary transcripts, copy source text
into project memory, add an apply command, or create a persistent proposal
queue.

Pending learning uses `resources/learning-lifecycle.md`. Showing a proposal
never consumes or resolves a pending observation.

## Scenario dispatch

After applying this core contract and the `hub-task-overview` contract, read
exactly the matching scenario resource:

- `day-plan` → `resources/day-plan.md` and its referenced calendar context;
- `evening-review` → `resources/evening-review.md`;
- `weekly-review` → `resources/weekly-review.md`.

Scenario resources provide output/detail rules only. They cannot override the
scope, allowed roots, secret handling, canonical sources, write policy,
or proposal schema in this core `SKILL.md` or in the `hub-task-overview`
contract.

Use the personal-assistant contract in `hub-task-overview` (scope, inputs, proposal envelope, write boundary).

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
   the compact task index rule in `hub-task-overview`; other project routing follows the Hub
   router's metadata-only candidate rules.
4. **Establish scope before richer reads.** Personal-assistant workflows use
   only their read boundary in `hub-task-overview`. Otherwise wait for explicit confirmation of
   the project or named project set and repeat every project ID and exact
   registered path. Read only the smallest required canonical `ai/` records and
   explicitly selected knowledge paths; never widen scope silently.
5. **Perform semantic analysis.** For `day-plan`, first synchronize from the
   complete fresh calendar response and reload changed canonical task records,
   as required by `resources/day-plan.md`. Then The AI agent extracts meaning, classifies and
   ranks work, and renders the selected scenario contract. Bash may validate
   paths, flags, and structured field syntax only. Ground output in the selected
   source or permitted canonical records and label inference.
6. **Apply or suggest after analysis.** Apply user-stated changes directly and
   report each exact target and diff. Show agent-generated ideas as
   suggestions. Unknown targets become questions rather than guessed writes.

## Preserved learning lifecycle

Only when `goals` is listed in `ai/modules.md`: for numeric goals, day
planning may render the existing goal-progress result, evening review may
record a user-stated `goal_progress` entry directly, and weekly review may render
pace/forecast.

Day planning may record noncanonical friction and calendar snapshots through
`snapshot-calendar.sh`.

Only when `learning` is listed in `ai/modules.md`: evening review reads
pending friction and may offer one `add_observation` proposal per grounded
issue. Proposal display leaves it pending. Acceptance or rejection resolves
it according to `resources/learning-lifecycle.md`;
accepted observations are appended to the journal before resolution,
rejection resolves without append, and failed append remains pending.
Weekly review may offer `promote_rule` for repeated observations and
`retire_rule` for contradicted or excess rules after the workflow-memory
check. Observation and promotion changes are applied once accepted; `retire_rule`
deletes a rule and waits for an explicit yes.
