# Current Task

Task ID: TASK-ai-dev-architecture-20261013-001
Status: active
Stage: plan

## Goal

Give the weekly review deterministic numbers on token waste in Hub sessions
(losses and startup cost), so the user can decide what to fix first.

## Scope

Design: `docs/superpowers/specs/2026-10-14-session-cost-diagnostics-design.md`
(approved in chat 2026-10-14). A script without a model counts losses
(error retries, repeated commands, repeated reads) and startup cost; the
weekly review shows the table and three ranked conclusions. The cheap-model
scanner is not changed. Nothing is fixed automatically.

Out of scope: dead-code and tech-debt checks (FT-20261013-001).

## Relevant files

- `modules/learning/scripts/session_cost.py` (new), `session_collect.py`
- `modules/learning/module.md`, `modules/learning/tests/`
- `modules/planning/skills/hub-workflows/resources/weekly-review.md`
- Hub `ai/architecture.md` § Transcript read exception

## Done criteria

1. `session_cost.py week` reports totals, losses by category and startup for
   both tools, matching the spec, with no argument, outside path or message
   text in its output.
2. Tests cover every fixture case in the spec; the whole learning test suite
   passes.
3. The weekly review resource shows `## Технические потери` with three ranked
   conclusions.
4. The architecture rule and module passport name the new script.
5. Deployed to the Hub and run once on the real previous week; result shown
   to the user.

## Agent handoff

Last agent: Claude Code
Last completed task: TASK-ai-dev-architecture-20261010-007.
Plan written 2026-10-14: docs/superpowers/plans/2026-10-14-session-cost-diagnostics.md; waiting for the user to review it and choose how to run it.
