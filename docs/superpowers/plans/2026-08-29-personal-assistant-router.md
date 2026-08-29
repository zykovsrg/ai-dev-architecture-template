# Personal Assistant Router Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route cross-project personal-assistant requests before single-project routing, while retaining explicit approval before every mutation.

**Architecture:** Extend `hub-project-router` with an intent-first branch. General planning and capture requests go to the existing proposal-only `hub-workflows`; project confirmation remains unchanged for project work. `hub-workflows` gains a bounded all-active-project read scope and one selectable package confirmation model.

**Tech Stack:** Markdown architecture and skills; Bash contract tests in `scripts/hub-smoke-test.sh`; existing hub installer and updater scripts.

## Global Constraints

- Read only `ai/current-task.md`, `ai/future-tasks.md`, and `ai/paused-tasks.md` from active projects in personal-assistant mode.
- Do not read code, knowledge records, credentials, arbitrary files, or inactive/archived projects through that mode.
- Every mutation, deletion, move, state change, Calendar operation, or external operation requires explicit confirmation.
- One package confirmation may approve only the unchanged named proposals shown in that package.
- Preserve the existing project-routing confirmation boundary for project-specific work.

---

### Task 1: Add failing smoke-test contracts

**Files:** Modify `scripts/hub-smoke-test.sh`.

**Interfaces:** Produces `personal_assistant_router_contract_valid` and extended `hub_workflows_skill_contract_valid` assertions.

- [ ] Add a validator requiring the router skill to name: `personal-assistant request`, `day plan`, `capture`, `all active registered projects`, the three canonical task files, the ban on code/knowledge/credentials/arbitrary-file reads, `project-specific request`, and `explicit project confirmation`.
- [ ] Extend the workflow validator to require `all active registered projects`, `personal and work`, `one selectable proposal package`, and `unchanged named proposals`.
- [ ] Run `bash scripts/hub-smoke-test.sh`; it must fail before the policy changes.
- [ ] Add negative mutation checks for a router without `all active registered projects` and a workflow without `one selectable proposal package`.
- [ ] Commit: `git add scripts/hub-smoke-test.sh && git commit -m "test: require personal assistant routing contracts"`.

### Task 2: Change template entry and router rules

**Files:** Modify `hub-template/AGENTS.md`, `hub-template/CLAUDE.md`, and `hub-template/ai/skills/hub-project-router/SKILL.md`.

**Interfaces:** Consumes an unconfirmed user request; produces a personal-assistant route, unchanged project route, or one clarification question.

- [ ] Replace unconditional first-project routing in both entry files with intent-first routing: day plans, cross-project status, reviews, capture, and cross-project search go to `hub-workflows`; project work keeps project confirmation.
- [ ] Add router intent classification before compact-index matching: personal-assistant request, project-specific request, architecture request, ambiguous request.
- [ ] Define the bounded personal-assistant read allowlist and personal/work output separation.
- [ ] Run `bash scripts/hub-smoke-test.sh`; router checks must pass while the workflow-package check fails until Task 3.
- [ ] Commit: `git add hub-template/AGENTS.md hub-template/CLAUDE.md hub-template/ai/skills/hub-project-router/SKILL.md scripts/hub-smoke-test.sh && git commit -m "feat: route personal assistant requests first"`.

### Task 3: Change hub workflow policy

**Files:** Modify `hub-template/ai/architecture.md` and `hub-template/ai/skills/hub-workflows/SKILL.md`.

**Interfaces:** Consumes the router personal-assistant route and active registered projects; produces read-only results or an exact selectable proposal package.

- [ ] Document all-active-project reading for the three canonical task files, without project-by-project confirmation; keep richer reads behind exact confirmed scope.
- [ ] Define one capture package: every proposal retains its ID, target, exact diff, and independence; the user may exclude items; a changed selected diff needs new confirmation.
- [ ] Run `bash scripts/hub-smoke-test.sh`; it must pass, including positive and negative contract checks.
- [ ] Commit: `git add hub-template/ai/architecture.md hub-template/ai/skills/hub-workflows/SKILL.md scripts/hub-smoke-test.sh && git commit -m "feat: allow personal assistant active-project overview"`.

### Task 4: Refresh documentation and installed hub

**Files:** Modify `README.md` and `getting-started/help.md`. Update managed installed-hub files only when the documented updater preview reports differences.

**Interfaces:** Consumes verified template changes and updater preview; produces an updated installed hub only when needed.

- [ ] Explain that `Покажи дела на сегодня` and `Разбери встречу` do not need project selection, while writes wait for one reviewed package confirmation.
- [ ] Run `bash scripts/check-consistency.sh` and `bash scripts/hub-smoke-test.sh`; both must pass.
- [ ] Run the documented updater in dry-run mode and inspect its managed differences.
- [ ] Apply only needed managed hub changes; do not modify unrelated projects.
- [ ] Re-run installed-hub verification and commit source documentation: `git add README.md getting-started/help.md && git commit -m "docs: explain personal assistant workflows"`.

## Completion audit

- [ ] Template has intent-first routing, bounded active-project reads, retained project confirmation, and selectable package confirmation.
- [ ] Template checks pass.
- [ ] Installed hub either matches changed managed template files or needed no update.
- [ ] No unrelated registered project was modified.

