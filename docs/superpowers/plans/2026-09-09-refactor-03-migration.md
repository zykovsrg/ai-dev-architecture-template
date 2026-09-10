# Hub-Only Project Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: `superpowers:executing-plans`. Execute M01–M06 after T05 with the constraints and roots in [the complete plan](/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture/docs/superpowers/plans/2026-09-09-refactor-complete.md).

**Goal:** Remove independent generic rule sets while retaining project memory, custom skills and recoverability.
**Architecture:** Per-project explicit migration manifests classify exact files before changes. Central hub workflows replace generic rules. Project-local extensions remain local and are discoverable through project context.
**Tech Stack:** Standard-library Python for file inventory/manifest checks, existing Git and shared project workflows. No application code scan.

## M01 — Exact project migration inventory (Terra)

**Create:** `scripts/project_architecture_migration.py`, `tests/test_project_architecture_migration.py`, `docs/audits/2026-09-09-hub-migration.md`.
**Read:** registry, selected project entry/rule/skill resources, standalone template and shared hub source. Do not inspect arbitrary `.env`, credentials or application source.
**Interface:** `scan --hub PATH --project-id ID --source PATH` emits manifest JSON; `check --hub PATH --project-id ID --manifest PATH` checks scope/source freshness only. No deletion in scan/check.

- [ ] Write tests with a temporary hub registry and three fixture projects: exact generic copy, custom file, generic skill with one different supporting resource. Add unregistered directory, symlinked ancestor, omitted source, path traversal, user-edited-after-scan cases.
- [ ] Resolve exactly one registry entry and its physical direct-child path under `<hub>/projects`. Candidate entry files: `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, `ai/external-tools.md`. Inventory `ai/skills/`, `.agents/skills/` and `.claude/skills/` only where they actually exist; inspect configuration keys only if explicitly required to route those skills, never dump an entire config file.
- [ ] Hash every package file, including references/templates/scripts. Package equivalence means equal relative file sets, bytes and relevant mode bits. A matching SKILL.md alone does not authorize package deletion.

```python
def classify_package(project_files, template_files):
    if project_files == template_files:
        return "generic-copy"
    if not template_files:
        return "project-extension"
    return "mixed-or-modified"
```

Here file maps contain relative path → `(sha256, executable-bit)`; the maps are built with symlink rejection. Empty folders alone are not evidence of a meaningful extension.

- [ ] Manifest fields: format, project ID/path, source template digest, entry/source hashes, and rows `{path, before_sha256, before_mode, action, target, reason, after_sha256}`. Actions `keep`, `remove-file`, `replace-file`, `move-file`; targets are explicit project-local relative paths. Until after-content is known, a proposed modified row remains `needs-review` and cannot apply.
- [ ] For modified generic skills, identify the project-specific delta from current and historical generic source, preserving genuine custom behavior. Known examples to examine: `frontend-design`, both different `bugfix-workflow` variants, architecture `session-audit`; older `task-finish`/`task-intake` differences may be historical general rules, not custom behavior. Record the evidence rather than classifying by name.
- [ ] Make the summary list only project ID, manifest path, counts, blocked reason and disposition. Do not copy private task descriptions into the central audit.
- [ ] Run `python3 -m unittest discover -s tests -p test_project_architecture_migration.py -v`; commit `feat: inventory exact project architecture migration targets`.

## M02 — Safe apply/restore and minimal project entry (Terra)

**Modify:** M01 helper/tests; `hub-template/ai/skills/hub-project-register/SKILL.md`, `hub-project-migrate/SKILL.md`, `hub-environment-check/SKILL.md`; `hub-template/ai/architecture.md`.
**Runtime:** each selected project `ai/migrations/2026-09-09-hub-only.json`; backup under its ignored `.local/architecture-migration/<operation-id>/`. Add exactly `/.local/architecture-migration/` to that project's ignore file if missing, showing it in the same manifest.

- [ ] Implement `apply --hub PATH --project-id ID --manifest PATH --confirm-manifest SHA` and `restore` with the same scope. Check manifest digest, registered physical path, all before-hashes, destination absence/expected hash and complete row dispositions before any file changes. `needs-review` blocks apply.
- [ ] Stage replacement bytes and backups first. Reuse R02's small path/hash primitives through a shared import only if needed; do not create a general workflow framework. Apply file-by-file and journal changes. On failure restore named targets that still match the operation's after-state; retain later user edits as conflicts.
- [ ] Removal is `unlink` of exact manifest files after backup. Remove an empty parent only with `rmdir`; never recursive delete `ai/skills`, `.claude`, `.agents` or a workspace. Preserve non-listed content. Restore preserves original modes and nonexistent-before state.
- [ ] Prefer keeping genuine extensions at their existing project-local locations. Add a concise `## Local extensions` list to project context with path/purpose; the shared workflow reads only relevant listed resources. No need to invent a second extension framework or copy custom skills to every project.
- [ ] Replace legacy AGENTS/CLAUDE contents with minimal hub pointers during pilots. Use the same body for both clients, differing only in heading. Exact template:

```markdown
# Project entry — hub managed

General workflows and access rules are owned by the enclosing Personal AI Hub.
Read the enclosing hub entry and route through its project registry before project work.
This file grants no additional project access.
Project-specific context and any local extensions remain in this project's ai/ memory.
Do not install or restore an independent generic rule set here.
```

For a confirmed registered project, resolve the enclosing hub by its registered path; do not follow an arbitrary external pointer. If direct-open clients already load hub rules reliably in the pilot, the manifest may remove the pointer instead. The accepted result must show how each supported client reaches hub instructions. A small routing pointer is not a maintained standalone architecture.
- [ ] Adapt environment/register/migrate instructions so already registered projects can use this migration without a physical move or fresh registration. Remove assumptions that every project needs generic `ai/skills` or project `ai/architecture.md`.
- [ ] Test exact generic removal, extension preservation, supporting resource preservation, interruption restore, late user edit, empty-directory cleanup and a repeated apply returning unchanged. Commit `feat: migrate project rules with explicit reversible manifests`.

## M03 — Three real pilots (Terra)

**Selected projects:** `hadassah-drive-images` (simple legacy), `content-plan-release-backlog` (nonstandard paused memory), `horizon-task-tracker` (custom diagnosis/design resources). Exact paths are `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/` plus these registered IDs; verify each registry path before access. If one no longer exists, select the first remaining project in the same category from M01 and record the reason; do not invent a replacement path.
**Modify:** only each pilot's approved manifest paths and migration record. Read-only access to task/knowledge/application assets does not authorize their deletion.

- [ ] Verify T04 normalization for the three pilots. Run safe source release tests; regenerate the release manifest. Preview a live update and inspect all preserved R01 behaviors. Apply the exact reviewed intermediate release using R03, retaining its recovery ID. This is the first runtime deployment, not part of planning.
- [ ] Show the three concrete migration manifests together as a reviewable package. The user has authorized the programme; only unresolved deletion of ambiguous custom behavior needs a new decision. Every exact removal must already be proven generic or replaced.
- [ ] Apply one pilot at a time. Record before/after hashes, remaining extensions, memory preservation and local commit. Do not commit unrelated app files.
- [ ] Check direct-open routing in each supported client: the agent reads hub rules, selects the right registry entry, respects memory scope and can find the pilot's relevant local extension. Use a read-only task such as identifying the current task's next action; do not alter project work just for the test. If only one client is available, mark the other unverified and keep its pointer.
- [ ] Run project-scoped task parser/board preview and registry validation. Compare all task/knowledge bytes with their approved normalization state. Trigger safe restore on a disposable clone of one pilot manifest and verify exact recovery before declaring the migration process reusable.
- [ ] Update `docs/audits/2026-09-09-hub-migration.md`. Commit `refactor: pilot hub-managed project rules` only for architectural pilot changes in their own repositories.

## M04 — Remaining registered projects (Terra or Luna on exact manifests)

**Files:** one project at a time, only M01/M02 manifest targets. Includes architecture project's own legacy setup, after the shared hub is deployed; includes archived projects without changing their archived status.

- [ ] Refresh the registry and manifest before each project. Require all hashes and custom dispositions to match. Changed input produces a focused reclassification, not a replay of a stale delete list.
- [ ] Apply the verified M02 procedure to one project, run scoped parser/preview and compare preserved resources. Record disposition: `migrated`, `already-hub-only`, `blocked-specific-item`. Do not use the old count 34 as an assumed deletion count.
- [ ] Projects with no generic copies still get a compatibility check, not artificial new files. Projects with private/medical content keep it local; central summaries only contain IDs/status.
- [ ] Commit one project's exact architecture changes, record restoration path, then continue. Luna stops on unclassified semantic differences; Terra resolves only from existing evidence/approved requirements.
- [ ] Final set equality: every current registry ID appears exactly once in the migration summary; no unregistered ID is changed. Historical removed IDs are retained only as historical rows. No open unresolved row is labeled migrated.

Commit message per project: `refactor: use shared hub workflows`. This is a finite loop over the current registry, not a proposal to plan the other projects later.

## M05 — Retire standalone entry paths and obsolete release code (Terra)

**Modify:** `scripts/install.sh`, `scripts/update-installed-architecture.sh`, `scripts/install-hub.sh`, `scripts/check-consistency.sh`, `scripts/smoke-test.sh`, `scripts/hub-smoke-test.sh`, `README.md`, `docs/install.md`, `getting-started/help.md`.
**Remove after dependency check:** exact files under `template/` and old standalone-only script resources that have no active consumer. Record each in the final retirement manifest; do not remove the new project's memory scaffold or migration reference material still required to compare old versions.

- [ ] Add installer tests before changes: no mode → hub; explicit `--mode hub` → hub; `--mode standalone` → explanatory nonzero with no files created; existing managed project target → nonzero with no writes. Old standalone updater invocation must never reinstall copied rules.
- [ ] Replace the final mode dispatch in `install.sh` with:

```bash
MODE="${MODE:-hub}"
case "$MODE" in
  hub) exec "$SCRIPT_DIR/install-hub.sh" "$TARGET_DIR" ;;
  standalone)
    printf '%s\n' 'Standalone installation is retired. Use the Personal AI Hub and register or migrate the project.' >&2
    exit 2
    ;;
  *) usage ;;
esac
```

Keep argument validation and hub naming/path safeguards. Delete interactive fallback to standalone and the final `rsync --ignore-existing` standalone copy branch. Old updater becomes an explanatory migration stub; it must not guess the enclosing hub and update it without a preview.
- [ ] `install-hub.sh` uses R03 for existing hubs; create-if-missing memory semantics for new hubs remain. It cannot silently restore a retired path just because an old template still contains it.
- [ ] Search executable references to `template/`, old generic skills, legacy bridge helpers and standalone updater. For each, either replace with shared hub equivalent or preserve a clearly named migration-only reference. Build a path-by-path retirement list; removal is permitted only after zero active consumers. Keep old-format test fixtures where they test actual backward compatibility.
- [ ] Rewrite consistency tests around the hub's two entry files and release manifest. Remove assertions that require six duplicated rule copies; preserve content/permission invariants and test genuine mismatch. Retire the standalone-only smoke suite branches, not the hub installation tests.
- [ ] Update help/default commands and remove instructions that reinstall per-project generic skills. Run installer, release, hub smoke and consistency suites. Commit `refactor: retire standalone installation paths`.

## M06 — Resolve ownership and stale architecture memory (Terra)

**Modify:** architecture project's `ai/future-tasks.md`, `ai/decisions.md`, `ai/changelog.md`, relevant context; `HUB_ROOT/ai/project-registry.md` and `ai/project-cards/hub-session-audit.md` only for the historical audit project's status; its local context/runbook pointers.

- [ ] Verify actual completion before closing `FT-20260813-001`, `FT-20260815-001`, `TASK-ai-dev-architecture-20260814-002` and older migration/knowledge/active-project entries. Partially complete work stays open with the exact missing criterion. Do not erase their change history.
- [ ] Retain architecture project memory as project data, tracked through its own repository under the same policy as other projects; shared runtime code is in release sources. Remove obsolete blanket exclusions for that memory only if they actually exist and after checking tracked private data. No change to credential-ignore rules.
- [ ] Mark superseded decisions with successor references; remove conflicting active Mode/confirmation rules that duplicate or contradict the current hub. Update the shared routing text rather than spreading new copies.
- [ ] Historical `hub-session-audit` has one owner, `ai-dev-architecture`. Mark historical docs superseded with a pointer to the current session-review procedure; preserve the history. Archive the registry/card status only after confirming no unrelated current work is active; if there is active work, transfer its explicit audit ownership without silently discarding that task.
- [ ] Run registry validator and check links in changed documents; commit local scoped changes as `docs: reconcile architecture ownership and migration history`.
