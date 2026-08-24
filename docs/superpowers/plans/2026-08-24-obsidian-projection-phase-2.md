# Obsidian Project Board — Implementation Plan

> **For agentic workers:** execute task by task with `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**Goal:** Create one safe generated Kanban board for 35 projects without a second task database.

**Architecture:** A Bash generator reads only a confirmed project set, returns a no-write preview, and can replace only the board and its manifest in the copied vault after fresh user confirmation.

**Tech Stack:** Bash, awk, sed, sort, shasum, Markdown, JSON, existing obsidian-kanban.

## Constraints

- Architecture records are canonical; board and manifest are projections.
- Allowed reads: project card, `ai/current-task.md`, `ai/future-tasks.md`, `ai/paused-tasks.md` for confirmed IDs only.
- Never read code, `knowledge/`, `Memory entry point`, or original vault.
- No new plugin or dependency.
- Only output targets: `tmp/obsidian-vault-copy/Obsidian/AI-архитектура/Projects/_views/Projects-Kanban.md` and adjacent `Projects-Kanban.manifest.json`.
- Preview writes nothing. `--write` requires an explicit flag and a fresh conversational approval.
- Blank, `complete`, `none`, checkbox, and old Kanban text are never converted; use Incoming + `нужно проверить`.
- Preserve unrelated working-tree changes.

## Files

- Create `scripts/generate-obsidian-projects-kanban.sh`: validation, reading, classification, rendering, guarded write.
- Create `scripts/obsidian-projects-kanban-test.sh`: disposable-fixture tests.
- Modify `scripts/hub-smoke-test.sh`: generator safety contract without real-project reads.
- Modify only after separate architecture-update approval: `ai/decisions.md` and `docs/superpowers/specs/2026-08-23-obsidian-projection-design.md` for Archived.

## Task 1 — approve durable Archived rule

- [ ] Show the exact replacement before editing:

```text
Incoming / Planned / Active / Waiting / Paused / Completed
```

becomes:

```text
Incoming / Planned / Active / Waiting / Paused / Completed / Archived
```

- [ ] After `Replace this?` approval, add: `Archived — registered Status: archived; no task actions are exposed.`
- [ ] Run `bash scripts/check-consistency.sh`; expect exit 0.
- [ ] Commit only the approved decision and durable spec files with message `docs: add archived Obsidian board column`.

## Task 2 — write failing test contract

- [ ] Create `scripts/obsidian-projects-kanban-test.sh` with a `mktemp -d /private/tmp/obsidian-projection.XXXXXX` fixture and cleanup trap.
- [ ] Make synthetic card/task fixtures for active, ready future, waiting-only, paused-only, completed, archived, and legacy `Status: complete` projects.
- [ ] Assert one card per fixture, legacy to Incoming with `нужно проверить`, preview creates no files, and invalid scope paths fail.
- [ ] Run the test before generator exists; expect failure for missing `scripts/generate-obsidian-projects-kanban.sh`.
- [ ] Commit: `test: define Obsidian board contract`.

## Task 3 — implement safe reader and classifier

- [ ] Create `scripts/generate-obsidian-projects-kanban.sh` accepting `--hub <absolute-path>`, `--scope <id-file>`, `--vault <copied-vault>`, and exactly `--preview` or `--write`.
- [ ] Reject relative hub path, duplicate/unregistered ID, missing allowed file, symlink, original-vault path, vault outside hub, unknown flag, and write without `--confirm-generated-write`.
- [ ] Resolve every registry path inside `<hub>/projects/`; read only the three agreed memory files and card.
- [ ] Implement exact precedence:

```text
archived -> Archived
actionable current -> Active
waiting only -> Waiting
paused only -> Paused
ready future -> Planned
canonical completed -> Completed
otherwise -> Incoming
```

- [ ] Run focused tests; expect all fixture classifications pass and no preview write.
- [ ] Commit: `feat: classify safe Obsidian board cards`.

## Task 4 — render deterministic preview

- [ ] Render columns in order: Incoming, Planned, Active, Waiting, Paused, Completed, Archived.
- [ ] Card fields: ID, name, purpose, safe status, due or `нет срока`, maximum seven structured actions. Archived has only ID, name, purpose, archived status.
- [ ] Render manifest keys: `format_version`, `generated_at`, `target`, `sources`; each source has ID, registered paths, SHA-256 hash, and no task body or knowledge path.
- [ ] Test ID ordering, fixed-time byte-identical preview, one card per project, and absence of task-body sentinel in manifest.
- [ ] Commit: `feat: preview generated Obsidian board`.

## Task 5 — implement guarded write

- [ ] Add failing tests for write without flag, outside-target write, symlinked `_views`, exactly two generated files, and manual board edit.
- [ ] Write temporary board and manifest inside target directory; validate hashes; rename only to exact target paths.
- [ ] Compare existing board hash with manifest. Difference stops with `proposal pending`; canonical files stay unchanged.
- [ ] Run tests; expect manual edit blocks replacement and task fixture files remain byte-identical.
- [ ] Commit: `feat: guard generated Obsidian board writes`.

## Task 6 — integrate and make real preview

- [ ] Add static safety assertions to `scripts/hub-smoke-test.sh`; it must not read real task files.
- [ ] Run focused test, `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, and whitespace check; expect exit 0.
- [ ] After a confirmed 35-project scope, run real preview only. Show board, warnings, and exact two-file diff.
- [ ] Stop for a new exact board-and-manifest write confirmation.
- [ ] Commit: `test: verify Obsidian board safety`.

## Rollback

Revert generator commits to remove code and tests. After a separately approved copied-vault write, restore or remove only `Projects-Kanban.md` and `Projects-Kanban.manifest.json`; never change project memory, old notes, Calendar, or original vault.
