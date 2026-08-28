# Projects Overview and Per-Project Boards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the global task Kanban with a three-column project overview linked to one validated editable Kanban per registered project.

**Architecture:** Canonical task records remain under each project's `ai/` directory. The generator publishes `Projects-Overview.md`, `Projects/<project-id>/Kanban.md`, and one manifest as an atomic set; the existing proposal scanner validates edits across all project boards before canonical writes. Existing `primary_archiproject` metadata supplies the overview group.

**Tech Stack:** Bash 3.2, Awk, sed, jq, SHA-256, Markdown, Obsidian Kanban, shell contract tests.

## Global Constraints

- `Projects-Overview.md` has exactly `Проект`, `Архипроект`, and `Текущая задача`.
- Every registered project gets `Projects/<project-id>/Kanban.md`, including archived projects and projects with no open tasks.
- Project boards are editable only through the existing proposal, validation, explicit-confirmation, and apply flow.
- `Tasks-Kanban.md` leaves the generated set and is removed only during the confirmed generated-view migration.
- Old manually maintained Obsidian boards are never changed.
- Project grouping is explicit after initial migration; runtime generation never infers it from tags.
- Preserve unrelated existing worktree changes.

---

### Task 1: Support group-only archiproject records

**Files:**
- Modify: `hub-template/ai/archiprojects.md`
- Modify: `scripts/check-hub-registry.sh`
- Modify: `scripts/hub-smoke-test.sh`
- Modify: `ai/decisions.md`

**Interfaces:**
- Consumes: the existing fenced YAML archiproject registry and project-card metadata.
- Produces: validated `kind: group|goal`; group records expose `id`, `name`, `status`, and `kind` without fake metrics.

- [ ] **Step 1: Write failing registry tests**

Add fixtures that accept:

````markdown
## hadassah

```yaml
id: hadassah
name: Хадасса
status: active
kind: group
```
````

and reject a group containing `target`, a goal missing `target`, or an unknown `kind`. Add a project card with:

```text
primary_archiproject: hadassah
archiproject_contribution: none
related_archiprojects: none
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `bash scripts/hub-smoke-test.sh`

Expected: FAIL because `kind` is unrecognized and the old validator requires `target`, `unit`, and `due`.

- [ ] **Step 3: Implement the conditional schema**

Update the parser to require exactly one `kind`. Validate fields with this contract:

```text
kind=group -> id,name,status,kind exactly once; target,unit,due absent
kind=goal  -> id,name,status,kind,target,unit,due exactly once
```

Allow `archiproject_contribution: none` only when the selected primary entry is `kind: group`; retain numeric contribution for `kind: goal`.

- [ ] **Step 4: Update the canonical template and decision**

Document both complete YAML forms in `hub-template/ai/archiprojects.md`. Record that overview grouping uses only a group record's `primary_archiproject`.

- [ ] **Step 5: Verify GREEN**

Run: `bash scripts/hub-smoke-test.sh`

Expected: `PASS` with all new positive and negative fixtures exercised.

---

### Task 2: Specify the three-column overview and isolated boards

**Files:**
- Modify: `scripts/obsidian-projects-kanban-test.sh`

**Interfaces:**
- Consumes: project registry, cards, `current-task.md`, `future-tasks.md`, `paused-tasks.md`, and archiproject registry.
- Produces: failing contract for `Projects-Overview.md`, per-project boards, and manifest format 4.

- [ ] **Step 1: Replace global-board fixture paths**

Define test targets:

```bash
OVERVIEW="$VAULT/Obsidian/Projects-Overview.md"
ARCHITECTURE_BOARD="$VAULT/Obsidian/Projects/ai-dev-architecture/Kanban.md"
WAITING_BOARD="$VAULT/Obsidian/Projects/waiting-project/Kanban.md"
MANIFEST="$VAULT/Obsidian/AI-Architecture.manifest.json"
```

- [ ] **Step 2: Add exact overview assertions**

Assert the header is exactly:

```markdown
| Проект | Архипроект | Текущая задача |
| --- | --- | --- |
```

Assert a row such as:

```markdown
| [[Projects/ai-dev-architecture/Kanban\|AI Dev Architecture]] | Дела | Current architecture task |
```

and assert `Status`, `Ready`, `Waiting`, and `Due` do not occur in the header.

- [ ] **Step 3: Add board-isolation and empty-board assertions**

Assert each board contains only anchors beginning with its own `<project-id>--`; assert a project without tasks still has all eight status headings and no task cards.

- [ ] **Step 4: Add migration and manifest assertions**

Require manifest format 4 with `.views.projects_overview` and `.project_boards[]` entries containing `project_id`, `target`, and `sha256`. Assert `Tasks-Kanban.md` is absent after a confirmed write.

- [ ] **Step 5: Run the contract test and verify RED**

Run: `bash scripts/obsidian-projects-kanban-test.sh`

Expected: FAIL because the generator still creates one global board and the six-column overview.

---

### Task 3: Generate and publish the new view set atomically

**Files:**
- Modify: `scripts/generate-obsidian-projects-kanban.sh`
- Test: `scripts/obsidian-projects-kanban-test.sh`

**Interfaces:**
- Consumes: validated explicit archiproject metadata and canonical task records.
- Produces: `Projects-Overview.md`, `Projects/<id>/Kanban.md`, manifest format 4, and atomic migration from format 3.

- [ ] **Step 1: Separate board rendering by project**

Accumulate task rows by `project_id`. Render every project with the existing ordered headings:

```text
Ideas Ready Active Waiting Blocked Review Paused Done
```

Keep card anchors as `<project-id>--<task-id>` and existing due-date syntax.

- [ ] **Step 2: Read explicit archiproject names**

Resolve each card's `primary_archiproject` against `ai/archiprojects.md`; fail on missing, `none`, unknown, duplicate, or non-group entries. Do not use tags after migration.

- [ ] **Step 3: Render the exact overview**

Escape table cells and render the linked name, resolved group name, and current goal or `—`. Do not calculate counts, status, or due dates for the overview.

- [ ] **Step 4: Write manifest format 4**

Use this shape:

```json
{
  "format_version": 4,
  "views": {
    "projects_overview": {"target": "Obsidian/Projects-Overview.md", "sha256": "..."}
  },
  "project_boards": [
    {"project_id": "ai-dev-architecture", "target": "Obsidian/Projects/ai-dev-architecture/Kanban.md", "sha256": "..."}
  ],
  "tasks": [],
  "sources": []
}
```

Retain the existing per-task source fields in `tasks`.

- [ ] **Step 5: Generalize the transaction**

Stage the overview, manifest, and all board files in one temporary tree; verify every hash; back up the previous generated set; replace it; restore the entire old set on any failed move. On the confirmed v3→v4 migration, remove only `Obsidian/Tasks-Kanban.md` after the new set is durable.

- [ ] **Step 6: Run the generator contract and verify GREEN**

Run: `bash scripts/obsidian-projects-kanban-test.sh`

Expected: `PASS: Obsidian project boards and project overview contract`.

---

### Task 4: Scan and apply edits from every project board

**Files:**
- Modify: `scripts/obsidian-task-sync.sh`
- Modify: `scripts/obsidian-task-sync-test.sh`
- Verify: `scripts/obsidian-task-sync-watch-test.sh`

**Interfaces:**
- Consumes: manifest format 4 and all listed project-board files.
- Produces: one combined proposal whose operations retain `project_id`, canonical source, and board hash evidence.

- [ ] **Step 1: Write failing multi-board proposal tests**

Create two project boards. Rename a task in one and move a task in the other. Assert one proposal contains both operations with their distinct `project_id` values. Add negative tests for a task anchor placed on the wrong project's board and for an unlisted board path.

- [ ] **Step 2: Run the sync test and verify RED**

Run: `bash scripts/obsidian-task-sync-test.sh`

Expected: FAIL because the scanner requires `Tasks-Kanban.md` and one `board_sha256`.

- [ ] **Step 3: Load boards only from the manifest**

Reject absolute targets, traversal, symlinks, duplicate project IDs, duplicate targets, missing boards, and targets outside `Obsidian/Projects/<project-id>/Kanban.md`. Parse each board with its manifest project ID; reject any anchor whose project prefix differs.

- [ ] **Step 4: Bind proposals to the complete edited set**

Replace scalar `board_sha256` with:

```json
"board_sha256": {
  "ai-dev-architecture": "...",
  "waiting-project": "..."
}
```

Verify every listed board hash and the manifest hash again before apply. Keep existing source-hash staging and rollback behavior unchanged.

- [ ] **Step 5: Refresh after confirmed apply**

Call the generator's confirmed architecture refresh. If refresh fails, roll back every canonical source and keep the proposal, matching current behavior.

- [ ] **Step 6: Verify GREEN and watcher compatibility**

Run:

```bash
bash scripts/obsidian-task-sync-test.sh
bash scripts/obsidian-task-sync-watch-test.sh
```

Expected: both scripts print `PASS` and exit 0.

---

### Task 5: Add canonical groups and explicit project membership

**Files:**
- Create: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/archiprojects.md`
- Modify: `/Users/zykovsrg/Documents/vibecode/_ai-hub/ai/project-cards/*.md`
- Verify: `scripts/check-hub-registry.sh`

**Interfaces:**
- Consumes: the 44 registered project cards and the approved initial mapping rule.
- Produces: four group records and one explicit primary group for every registered project.

- [ ] **Step 1: Add four group records**

Create `hadassah` (`Хадасса`), `businka` (`Бусинка`), `dela` (`Дела`), and `masha` (`Маша`) as `status: active`, `kind: group`.

- [ ] **Step 2: Add explicit metadata to every card**

For every card referenced by the current hub registry, write exactly:

```text
primary_archiproject: <hadassah|businka|dela>
archiproject_contribution: none
related_archiprojects: none
```

Use `hadassah` only for cards whose registry tags include `hadassah`, `businka` only for `zdorove-businki`, and `dela` for all remaining current cards. Assign none to `masha`.

- [ ] **Step 3: Run registry validation**

Run: `bash scripts/check-hub-registry.sh`

Expected: `Registry check passed: 44 projects`.

---

### Task 6: Update durable documentation and verify the whole change

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/install.md`
- Modify: `docs/update-installed-projects.md`
- Modify: `docs/superpowers/specs/2026-08-23-obsidian-projection-design.md`
- Modify: `docs/superpowers/specs/2026-08-24-obsidian-projection-phase-2-design.md`
- Modify: `scripts/update-installed-hub.sh` if the installed-file allowlist changes

**Interfaces:**
- Consumes: completed generator, sync, migration, and schema behavior.
- Produces: consistent user and architecture documentation with no references treating `Tasks-Kanban.md` as current.

- [ ] **Step 1: Update docs and stale references**

Document the three-column overview, per-project board location, proposal-only edits, format-4 migration, and explicit group metadata. Preserve historical plan/spec text unless it is an active durable contract.

- [ ] **Step 2: Run focused tests**

Run:

```bash
bash scripts/hub-smoke-test.sh
bash scripts/obsidian-projects-kanban-test.sh
bash scripts/obsidian-task-sync-test.sh
bash scripts/obsidian-task-sync-watch-test.sh
```

Expected: every command exits 0 and prints `PASS`.

- [ ] **Step 3: Run repository-wide verification**

Run:

```bash
bash scripts/check-consistency.sh
bash scripts/smoke-test.sh
git diff --check
```

Expected: all commands exit 0 with no diff whitespace errors.

- [ ] **Step 4: Preview the real vault migration**

Run the generator with the real hub, all-project scope, local architecture vault, and `--preview`. Verify the preview lists 44 project boards, the exact overview columns, and deletion of only the generated `Tasks-Kanban.md`. Do not write the real vault without a separate confirmation.

- [ ] **Step 5: Review the final diff**

Confirm that unrelated pre-existing changes in `ai/future-tasks.md`, `scripts/assistant-workflows.sh`, and `scripts/assistant-workflows-test.sh` were not overwritten or included accidentally.
