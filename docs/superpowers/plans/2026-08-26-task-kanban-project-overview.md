# Task Kanban and Project Overview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the project-card Kanban with a task-card Kanban and a separate generated project overview.

**Architecture:** `Tasks-Kanban.md` contains one card per canonical task and columns matching task statuses. `Projects-Overview.md` is a Markdown table with one row per registered project. One combined manifest validates both files and blocks any rebuild after a manual edit to either generated view.

**Tech Stack:** Bash, Awk, SHA-256, jq, shell contract tests.

## Global Constraints

- `ai/` records remain canonical; Obsidian files are generated views only.
- `Tasks-Kanban.md` uses task statuses; it never derives task columns from project status.
- Future `promoted`, `done`, and `dropped` entries are not open task cards.
- Existing `Projects-Kanban.md` is not altered until a later preview and explicit vault-write confirmation.

---

### Task 1: Specify task cards and the project overview

**Files:**
- Modify: `scripts/obsidian-projects-kanban-test.sh`

- [ ] Change fixture expectations from one project card per column to task cards in `Ideas`, `Ready`, `Active`, `Waiting`, `Blocked`, `Review`, `Paused`, and `Done`.
- [ ] Add assertions that each task card includes its parent project and that promoted, dropped, and done future entries are hidden.
- [ ] Add assertions for a one-row-per-project overview table with current task, ready count, waiting count, and nearest due date.
- [ ] Add an assertion that editing either generated view blocks a subsequent write with `proposal pending`.
- [ ] Run the contract test and verify that it fails against the current one-board generator.

### Task 2: Generate cards from canonical task records

**Files:**
- Modify: `scripts/generate-obsidian-projects-kanban.sh`

- [ ] Parse the current-task goal and status into one current-task card when it is an open or completed task status.
- [ ] Parse every structured future entry into zero or one card according to its task status.
- [ ] Parse every structured paused entry into a paused card.
- [ ] Render task cards in status columns and include a project line on every card.
- [ ] Render `Projects-Overview.md` from registered project status and derived task summary fields.
- [ ] Run the contract test and verify it passes.

### Task 3: Make the manifest validate both views

**Files:**
- Modify: `scripts/generate-obsidian-projects-kanban.sh`
- Modify: `scripts/obsidian-projects-kanban-test.sh`

- [ ] Replace the board-only manifest with `AI-Architecture.manifest.json`, version 2, containing SHA-256 hashes and paths for both generated files.
- [ ] Require all three generated files to exist together before a rebuild.
- [ ] Stop with `proposal pending` if either generated view no longer matches the manifest.
- [ ] Write all generated files via temporary files and validate their hashes before replacement.
- [ ] Run the contract test and verify it passes.

### Task 4: Update the durable design

**Files:**
- Modify: `ai/decisions.md`
- Modify: `docs/superpowers/specs/2026-08-23-obsidian-projection-design.md`
- Modify: `docs/superpowers/specs/2026-08-24-obsidian-projection-phase-2-design.md`

- [ ] Replace the one-project-card Kanban decision with the two-view contract.
- [ ] Record task-column mappings, overview columns, target paths, and combined-manifest behavior.
- [ ] State that the old project Kanban is removed only during a separately confirmed live-vault write.

### Task 5: Verify and commit the implementation

**Files:**
- Verify: task-board contract test, JSON manifest, and Git diff.

- [ ] Run `bash scripts/obsidian-projects-kanban-test.sh`.
- [ ] Run `git diff --check`.
- [ ] Commit only the generator, contract test, decision, specifications, and this plan with `feat: generate task Kanban and project overview`.
