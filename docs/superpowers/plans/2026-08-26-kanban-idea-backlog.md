# Kanban Idea Backlog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show each project's `idea` future tasks as a distinct backlog block in its generated Kanban card.

**Architecture:** `ready` entries remain actionable next steps and decide the Planned column. `idea` entries are rendered beneath a labelled `💡 Идеи / backlog` line, do not affect the project column, and are never mixed with ready actions.

**Tech Stack:** Bash, Awk, shell contract tests.

## Global Constraints

- Project and task records remain canonical; the board is a generated view.
- Only `idea` entries receive the new rendering; `blocked`, `promoted`, `done`, and `dropped` remain hidden.
- Manual board edits must still block replacement with `proposal pending`.

---

### Task 1: Specify the new rendered card

**Files:**
- Modify: `scripts/obsidian-projects-kanban-test.sh`

- [ ] Add an active-project fixture with two `idea` entries and one hidden `blocked` entry.
- [ ] Assert that both idea titles appear below `💡 Идеи / backlog`, while the blocked title stays absent.
- [ ] Run `bash scripts/obsidian-projects-kanban-test.sh` and confirm it fails before the generator change.

### Task 2: Render idea entries

**Files:**
- Modify: `scripts/generate-obsidian-projects-kanban.sh`

- [ ] Add a parser for `idea` entries using the same safe future-task format as `ready` entries.
- [ ] Store per-project idea titles separately from actionable next steps.
- [ ] Render the labelled idea block only when at least one valid idea exists.
- [ ] Run `bash scripts/obsidian-projects-kanban-test.sh` and confirm it passes.

### Task 3: Keep the design documentation current

**Files:**
- Modify: `docs/superpowers/specs/2026-08-23-obsidian-projection-design.md`
- Modify: `docs/superpowers/specs/2026-08-24-obsidian-projection-phase-2-design.md`

- [ ] State that all valid `idea` entries render in a separate labelled backlog block.
- [ ] State that they do not determine the project column.
- [ ] Verify the specification does not say that only ready entries can appear in a card.

### Task 4: Verify and commit

**Files:**
- Verify: generator contract test and Git diff.

- [ ] Run `bash scripts/obsidian-projects-kanban-test.sh`.
- [ ] Run `git diff --check`.
- [ ] Commit only the generator, test, specifications, and this plan with `feat: show future ideas in Kanban cards`.
