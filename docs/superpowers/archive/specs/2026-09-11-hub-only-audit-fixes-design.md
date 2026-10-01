# Hub-Only Audit Fixes — Design

## Goal

Make the Personal AI Hub the only supported architecture, remove the retired standalone distribution, fix the confirmed Hub defects found in the September audit, and reduce avoidable Hub context cost without weakening project isolation, confirmation gates, Obsidian integrity, Calendar safety, or the optional knowledge layer.

This design is authoritative for the 2026-09-11 audit-fix implementation. Older plans remain historical evidence; where they overlap, this design takes precedence.

## Core decision: Hub only

There is no longer a supported standalone architecture.

The supported model is:

```text
Personal AI Hub
→ registry routing
→ exact project confirmation when required
→ project memory
→ Hub-owned workflow
→ implementation/review
→ project Git + durable project memory
```

`hub-template/` is the only distributable architecture template.

The old `template/` standalone distribution, standalone installer/update flow, standalone documentation, and standalone-only smoke-test expectations must be retired after active references are removed.

A project may keep a tiny tool-entry pointer such as `AGENTS.md` or `CLAUDE.md` only when a supported client needs it to find the enclosing Hub. Such a pointer is routing metadata, not an independent architecture. It must not contain a second copy of generic workflows or security rules.

Project-local memory and genuine project-specific extensions remain local. Removing standalone must not delete:

- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
- `ai/session-reviews/`
- project-local knowledge
- confirmed project-specific skills or tool configuration

## Confirmed correctness fixes

### 1. Evening review must respect friction state

`prepare_evening_review()` currently reconstructs pending friction from the daily text file and ignores accepted/rejected state.

Required behavior:

- pending observations are returned;
- accepted observations are not returned;
- rejected observations are not returned;
- unresolved observations remain pending;
- a failed acceptance write must not silently resolve an observation.

The implementation must preserve the same observation ID formula and state semantics used by `scripts/workflow_friction.py`.

### 2. One learning lifecycle

The canonical lifecycle is:

```text
new friction
→ pending
→ proposal shown
→ still pending
→ explicit accept or reject
→ resolved
```

Showing an `add_observation` proposal never consumes or resolves friction.

After acceptance, the confirmed observation is written to the observation journal and then resolved as `accepted`. After rejection it is resolved as `rejected` without being written to the journal.

`hub-workflows/SKILL.md`, its learning resource, tests, and any runtime helpers must describe the same lifecycle.

### 3. Proposal schema must allow its own learning actions

The proposal envelope must support every action that `hub-workflows` actually emits.

At minimum this includes the existing general actions plus:

- `goal_progress`
- `add_observation`
- `promote_rule`
- `retire_rule`

A consistency test must fail if a workflow references an action missing from the canonical envelope schema.

### 4. Task-record aggregate path must work

`scripts/task_records.py` contains a CLI branch that calls missing `read_project_records()`.

Implement the aggregate function instead of deleting the branch because the same normalized aggregate is useful for the compact Hub task index.

It must combine current, future, and paused records for exactly one project while preserving the existing strict per-record validation.

### 5. Snapshot creation must be collision-safe

Calendar evening-review snapshots must use atomic unique file creation. Concurrent calls must not overwrite one another.

The filename may change as long as existing `YYYY-MM-DD-*` discovery continues to work and snapshot ordering remains deterministic enough for review history.

## Context-cost improvements

### Compact task index first

Personal-assistant workflows currently expose the full `current-task.md`, `future-tasks.md`, and `paused-tasks.md` contents of every active project to the model.

Replace that as the default first pass with a deterministic compact index generated from the same canonical files.

Each row should contain only fields needed for discovery/ranking, for example:

```text
project_id
task_id
title
status
due
source_kind
source_path
```

The compact index is derived data, not a new source of truth.

The model opens full canonical records only when the selected task or requested analysis needs details that the index does not contain. Project isolation and read permissions remain unchanged.

### Split the `hub-workflows` monolith by scenario

Keep one small `hub-workflows/SKILL.md` with shared authority, safety, scope, proposal, and confirmation rules.

Move scenario-specific long-form instructions into on-demand resources, at minimum:

- `resources/day-plan.md`
- `resources/evening-review.md`
- `resources/weekly-review.md`
- `resources/capture.md`

Do not duplicate the shared security or confirmation boundary inside every resource except for a short reference where needed.

The purpose is progressive disclosure, not a redesign of workflow behavior.

## Hub installation and release

### Installer

`scripts/install.sh` becomes Hub-only.

Required behavior:

- no mode specified → Hub install;
- `--mode hub` → Hub install;
- `--mode standalone` → clear nonzero retirement message and no writes;
- no interactive fallback to standalone;
- no `rsync` of `template/` into a project.

### Legacy standalone updater

`scripts/update-installed-architecture.sh` must never reinstall standalone rules.

Keep it only as a migration/retirement helper if active references still need it. Otherwise remove it after reference checks. If retained, it must explain that standalone is retired and direct the user to Hub registration/migration without modifying the project.

### Hub release path

Use one canonical Hub release mechanism. Prefer the existing content-addressed `scripts/hub_release.py` preview/apply model rather than maintaining a second independent updater implementation.

Existing transactional staging, hashes, conflict detection, backup, and rollback behavior must be preserved and tested.

When a remote branch such as `main` is used as a source, resolve it to one commit SHA before preview and use that same revision through apply. Preview and apply must never silently refer to different commits.

Documentation must not recommend `curl | bash`.

## Knowledge layer

The Hub knowledge layer stays.

These remain optional, on-demand capabilities:

- `hub-knowledge-enable`
- `hub-knowledge-capture`
- `hub-knowledge-review`

Knowledge is not default context and must not become an automatic archive of every task or conversation.

Standalone knowledge copies under the retired `template/` are removed with the standalone distribution. Hub knowledge behavior is otherwise unchanged unless a regression test reveals a Hub-specific defect.

## What is intentionally not being changed

Do not redesign working Hub behavior merely because the old standalone version had a problem.

Specifically:

- Hub `hub-task-intake` already creates project-scoped `Task ID`s; do not rewrite it for the retired standalone bug.
- Hub `hub-task-finish` has its own explicit closure semantics; do not change its confirmation model unless a Hub-specific failing test proves a contradiction.
- Keep current project selection and isolation rules.
- Keep Calendar preview/apply confirmation gates.
- Keep Obsidian canonical → projection → proposal → confirmed canonical apply.
- Keep project cards metadata-only.
- Keep `current / paused / future` as separate task classes.
- Keep Git as full history and project changelog/decisions as semantic memory.
- Do not add a database, daemon, background model worker, or new service.

A future state-machine simplification may be considered separately, but it is not required for this correctness and consolidation pass.

## Source-of-truth rules after the change

- Shared architecture rules and shared skills: Hub only.
- Project identity and path: Hub registry.
- Current work: project `ai/current-task.md`.
- Paused work: project `ai/paused-tasks.md`.
- Future work: project `ai/future-tasks.md`.
- Stable project orientation: project `ai/project-context.md`.
- Durable decisions: project `ai/decisions.md`.
- Semantic result history: project `ai/changelog.md`.
- Exact code/file history: Git.
- Optional detailed reusable knowledge: project knowledge layer.

## Test strategy

Use TDD for every behavior change:

1. add a focused regression test;
2. run it and observe the expected failure for the intended reason;
3. implement the minimum change;
4. rerun the focused test;
5. run the relevant integration/consistency suite;
6. review the diff before committing.

Required focused coverage includes:

- accepted/rejected friction no longer returned by evening review;
- proposal display does not resolve friction;
- learning action schema matches referenced actions;
- aggregate task-record CLI works;
- compact task index excludes inactive projects and does not expose full record bodies;
- concurrent snapshot writes produce distinct files;
- installer defaults to Hub and refuses standalone without writes;
- legacy standalone updater cannot restore standalone;
- Hub release rollback/conflict/plan-hash behavior remains correct;
- active docs/runtime have no dependency on `template/` after retirement;
- Hub knowledge skills remain present and on-demand.

Do not run application test suites from registered projects. This work changes the architecture repository and its Hub/calendar policy only.

## Acceptance criteria

The work is complete when:

1. Hub is the only supported install/runtime architecture.
2. `template/` has no active runtime or documentation consumer and is removed.
3. A retired standalone command cannot create or update standalone architecture files.
4. Evening review returns only truly pending friction.
5. Learning proposals and lifecycle use one consistent contract.
6. Every workflow action is valid under the proposal schema.
7. Aggregate task-record parsing works and powers a compact all-project first pass.
8. Full task files are loaded only when needed after compact discovery.
9. `hub-workflows` uses progressive scenario resources rather than one large monolith.
10. Calendar snapshots cannot overwrite each other under concurrent creation.
11. Hub release/update follows one reviewed content-addressed path and uses one source revision from preview through apply.
12. Knowledge skills remain optional and available.
13. Focused tests, Hub smoke tests, consistency checks, and Calendar policy tests pass.
14. No unrelated project code or user task memory is modified.