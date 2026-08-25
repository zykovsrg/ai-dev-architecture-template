# Stable Obsidian Vault Root Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep one local, Git-ignored Obsidian vault copy in this project and generate its only project board at the vault root.

**Architecture:** The generator accepts only `obsidian-vault/` beneath the registered architecture project. It writes `Obsidian/Projects-Kanban.md` and an adjacent manifest. The existing legacy notes, media, and legacy Kanban files remain untouched; only named Obsidian Sync conflict copies and one named trash file are removed after successful generation.

**Tech Stack:** Bash, POSIX filesystem tools, SHA-256, jq, Git worktree.

## Global Constraints

- Never access or alter the original external vault.
- `obsidian-vault/` is local-only and Git-ignored.
- The project `ai/` files and legacy vault content are not modified.
- A write must stop when a board differs from its manifest (`proposal pending`).

---

### Task 1: Change the generated-board contract

**Files:**
- Modify: `scripts/generate-obsidian-projects-kanban.sh`
- Modify: `scripts/obsidian-projects-kanban-test.sh`

**Interfaces:**
- Consumes: `--vault <architecture-project>/obsidian-vault`.
- Produces: `<vault>/Obsidian/Projects-Kanban.md` and `<vault>/Obsidian/Projects-Kanban.manifest.json`.

- [ ] Change the fixture’s expected vault directory to `obsidian-vault` and its board/manifest paths to the `Obsidian` root.
- [ ] Run `bash scripts/obsidian-projects-kanban-test.sh` and confirm it fails against the current generator’s old `tmp/…/AI-архитектура/…` contract.
- [ ] Update the generator’s allowed vault, target directory, manifest `target` value, symlink checks, and error text to the new root contract.
- [ ] Run `bash scripts/obsidian-projects-kanban-test.sh` and confirm it passes.

### Task 2: Update durable projection documentation

**Files:**
- Modify: `docs/superpowers/specs/2026-08-23-obsidian-projection-design.md`
- Modify: `docs/superpowers/specs/2026-08-24-obsidian-projection-phase-2-design.md`

**Interfaces:**
- Documents the Task 1 target and the local-only vault path.

- [ ] Replace the obsolete nested board target with `Obsidian/Projects-Kanban.md` and the adjacent manifest.
- [ ] State that `obsidian-vault/` is the permanent local copy and remains ignored by Git.
- [ ] Verify no current specification still names the obsolete generated output path.

### Task 3: Prepare and write the permanent vault copy

**Files:**
- Modify: `.gitignore`
- Move: `tmp/obsidian-vault-original-copy/` → `obsidian-vault/`
- Modify: `obsidian-vault/Obsidian/Projects-Kanban.md`
- Create: `obsidian-vault/Obsidian/Projects-Kanban.manifest.json`

**Interfaces:**
- Uses the Task 1 generator and an all-project scope file.

- [ ] Add `/obsidian-vault/` to `.gitignore`.
- [ ] Move the confirmed local copy without copying from the original external vault.
- [ ] Run the generator preview for the all-project scope and inspect the proposed board and manifest target.
- [ ] Run the generator write with `--confirm-generated-write`.
- [ ] Verify the root board hash matches its manifest and no nested `AI-архитектура/Projects/_views/Projects-Kanban.md` exists.

### Task 4: Remove explicitly approved local clutter

**Files:**
- Delete: the 57 exact `.obsidian/*sync-conflict*` or `*conflicted copy*` files listed in the preflight.
- Delete: `obsidian-vault/Obsidian/.trash/кате.md`.

**Interfaces:**
- Operates only after Task 3 verifies the board/manifest pair.

- [ ] Re-enumerate the approved conflict files and trash file immediately before deletion; stop if the list differs.
- [ ] Delete only those 58 files.
- [ ] Verify no matching conflict files and no `.trash` files remain, while `app.json`, `appearance.json`, `workspace.json`, and plugin manifests still exist.

### Task 5: Verify and commit the implementation

**Files:**
- Verify: Task 1 tests, generator preview/write checks, documentation paths, and Git diff.

- [ ] Run `bash scripts/obsidian-projects-kanban-test.sh`.
- [ ] Run a root-board/manifest SHA-256 check and `jq -e 'type == "object"'` on the manifest.
- [ ] Run `git diff --check` and review `git diff --name-only`.
- [ ] Commit only tracked implementation files with `feat: move generated Obsidian board to stable vault root`.
