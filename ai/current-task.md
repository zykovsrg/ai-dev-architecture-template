# Current Task

Status: review
Stage: review
Task ID: TASK-ai-dev-architecture-20261003-001

## Goal

Make evening review urgent-first and conversational, asking only about events
with active registered projects, one at a time.

## Relevant files

modules/planning/scripts/evening_review.py and its tests;
modules/planning/skills/hub-workflows/resources/evening-review.md;
modules/planning/rules.md and module.md.

## Done criteria

Selection and dialogue contracts verified; applicable architecture checks pass;
updated helper and skill deployed to the installed Hub with a read-only smoke test.

## Verification

Implementation installed in the Hub on 2026-10-03. Planning: 26 tests pass
(10 new selection/CLI tests). Architecture main suite: 197 pass; module
boundaries pass. Installation smoke passed with TMPDIR=/private/tmp after the
default macOS temporary path was rejected as a symlink. Optional module
removal checks rerun after final skill changes: 3 pass.
Guarded live input for review day 2026-10-02: full coverage, 9 eligible events,
10 skipped; first is the Tuychieva meeting. No Calendar changes during tests.
Installed managed-file preview has no pending changes.

## Agent handoff

Last agent: Codex
Last completed task: TASK-ai-dev-architecture-20261002-001.
Architecture corrections installed and verified. All remaining 66 active
projects inspected with exact-path batch confirmation. Task records pass;
41 project-context gaps are recorded as a future idea. Guarded live planning
reconciled 11 task schedules without changing Calendar, deadlines or statuses.
Reports: docs/audits/2026-10-02-all-project-compatibility.md and
docs/audits/2026-10-02-refactoring-assessment.md.
Session review: ai/session-reviews/2026-10-02-architecture-corrections-closure.md
Local changes are on codex/architecture-corrections-2026-10-02; no push or merge
is recorded. Follow-up needs project-specific facts, not assumed code refactors.
