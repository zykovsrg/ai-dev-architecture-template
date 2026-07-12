# Strict Task Boundary Design

Date: 2026-07-11

Status: approved by user (brainstorming session 2026-07-11)

## Problem

The architecture separates tasks weakly. `task-intake` and `task-switch` decide
"same task vs different task" with seven fuzzy criteria and agent judgment. In
real sessions several requests silently merge into one task: scope grows, the
recorded task stops matching the actual work, and `ai/current-task.md` loses
its value as the source of truth.

## Core change: presumption flip

Old model: a new request is treated as a continuation unless the agent decides
otherwise.

New model: **a new request is a different task by default.** It counts as a
continuation only when it fits the **recorded Done criteria** of the current
task:

- work that directly advances the recorded Done criteria;
- fixing or adjusting work just produced for this task;
- running tests, checks, or review of this same work;
- answering the agent's questions.

Everything else stops work and requires an explicit user decision.

## Decision point: request outside Done criteria

When a request does not fit the recorded Done criteria, the agent must stop
and ask one question with three options before doing any work:

1. **Extend the current task.** Allowed only with a written boundary update:
   the agent must update `Goal` and `Done criteria` in `ai/current-task.md`
   before starting the work. Silent scope growth becomes impossible.
2. **Switch** via `task-switch` (pause or replace per its normal flow).
3. **Save to `ai/future-tasks.md`** and continue the current task.

No work starts until the user answers.

## File changes

### `ai/skills/task-intake/SKILL.md` (+ template mirror)

Rewrite the "Existing unfinished current task" section:

- replace the seven-signal list with the single Done-criteria test;
- define the continuation whitelist (the four bullets above);
- add the mandatory three-option question for out-of-boundary requests;
- add the rule: extension requires updating `Goal` and `Done criteria` in
  `ai/current-task.md` before work starts.

### `ai/skills/task-switch/SKILL.md` (+ template mirror)

Align the "How to decide whether this is a different task" section with the
same Done-criteria model. Update examples accordingly. Phase 1 / Phase 2
mechanics stay unchanged.

### `AGENTS.md`, `CLAUDE.md` (+ template mirrors)

No new lines. Amend one existing Core Rules line:

- Old: `Prefer minimal diffs, clean architecture, and confirmed scope.`
- New: `Prefer minimal diffs, clean architecture, and confirmed scope; a request beyond the recorded Done criteria is a different task until the user confirms otherwise.`

Budget: about +95 bytes per file; no new lines.

### `ai/architecture.md` (+ template mirror)

- Version 6.10 → 6.11.
- Add a short task-boundary paragraph: Done criteria define the task boundary;
  extension requires a written update of the current-task file; details live in
  `task-intake` and `task-switch` skills.

## Out of scope

- `environment-check`, `task-finish`, docs pages, scripts — unchanged.
- Canonical lists (canon blocks) — untouched.
- FT-20260711-004 (deleting promoted future tasks) — separate task.

## Verification

- `bash scripts/check-consistency.sh` passes.
- `bash scripts/smoke-test.sh` passes.
- `cmp` equality for all changed root/template pairs.
- Entry-file size measured before/after; growth ≤ 110 bytes per file, no new
  lines.
- Manual scenario: mid-task, user asks for something outside Done criteria →
  agent asks the three-option question and does no work until answered.
- Codex/Claude semantic parity: `diff AGENTS.md CLAUDE.md` shows only the
  existing tool-specific wording differences.

## Risks

- Too-strict reading could nag the user on trivial follow-ups; mitigated by
  the explicit continuation whitelist.
- Vague or missing Done criteria weaken the boundary test; task-intake already
  requires observable Done criteria at task creation.
