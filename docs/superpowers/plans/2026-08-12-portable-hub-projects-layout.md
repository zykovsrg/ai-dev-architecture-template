# Portable Hub Projects Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Install a portable `_ai-hub` where every managed project is inside `_ai-hub/projects/`, and provide a separate preview-first migration workflow for legacy projects.

**Architecture:** The installer derives one allowed root, `<hub>/projects`, and the hub Git repository ignores that directory. Existing roots are not supported. `project-migrate` uses a separately confirmed temporary source only; it never adds that source to allowed roots.

**Tech Stack:** Bash, Markdown skills, Git.

## Global Constraints

- The sole permanent allowed root is `<canonical-hub>/projects`.
- Install creates `projects/` and Git ignores `/projects/`.
- Projects stay independent repositories; no project is inspected, moved, copied, or registered during install.
- Hub mode takes only its `_ai-hub` path; `--root` is rejected.
- Create/register accept direct children of the one projects root only.
- Migration needs a separately confirmed temporary source, preview, and explicit move approval; it preserves `.git/`, never overwrites, and stops after a failure.

---

### Task 1: Write failing portable-install checks

**Files:**
- Modify: `scripts/hub-smoke-test.sh`
- Modify: `scripts/smoke-test.sh`

- [ ] Add a clean install fixture: `bash scripts/install.sh --mode hub "$PORTABLE_HUB"`.
- [ ] Assert `projects/.gitkeep`, `/projects/` in `.gitignore`, and exactly `- $PORTABLE_HUB/projects` in `ai/allowed-roots.md`.
- [ ] Create `projects/fixture/.git` and assert `git -C "$PORTABLE_HUB" status --short` does not report the fixture.
- [ ] Assert rejection of hub `--root`, wrong hub basename, and non-hub nonempty target.
- [ ] Add a failing mandatory-skill assertion for `project-migrate`.
- [ ] Run `bash scripts/hub-smoke-test.sh`; expect failure before implementation.
- [ ] Commit: `test: define portable hub layout contract`.

### Task 2: Implement portable installation

**Files:**
- Modify: `scripts/install.sh`
- Modify: `scripts/install-hub.sh`
- Create: `hub-template/projects/.gitkeep`
- Modify: `hub-template/.gitignore`
- Modify: `hub-template/ai/allowed-roots.md`

- [ ] Replace hub CLI with `install.sh --mode hub [HUB_DIR]`; reject all `--root` arguments with a portable-layout explanation.
- [ ] Derive `PROJECTS_ROOT="$CANONICAL_HUB_DIR/projects"`, create it, and write it as the sole allowed-root entry.
- [ ] Add `/projects/` to hub `.gitignore` and retain only `projects/.gitkeep` in the empty template.
- [ ] Remove installer candidate discovery. It must state that no project is inspected or registered automatically.
- [ ] Run hub smoke test and `git diff --check`.
- [ ] Commit: `feat: install portable hub projects layout`.

### Task 3: Constrain ordinary hub workflows

**Files:**
- Modify: `hub-template/AGENTS.md`
- Modify: `hub-template/CLAUDE.md`
- Modify: `hub-template/ai/architecture.md`
- Modify: `hub-template/ai/skills/project-create/SKILL.md`
- Modify: `hub-template/ai/skills/project-register/SKILL.md`
- Modify: `scripts/check-hub-registry.sh`
- Modify: `scripts/hub-smoke-test.sh`

- [ ] Replace multi-root selection with validation of `<hub>/projects` in `project-create` and `project-register`.
- [ ] Make the registry validator reject missing, duplicate, external, or noncanonical allowed roots and project paths outside the projects directory before card or memory reads.
- [ ] Add unsafe external-root and outside-project-path fixtures to the hub smoke test.
- [ ] Keep confirmation, secret, and memory-isolation precedence unchanged.
- [ ] Run `bash scripts/check-consistency.sh` and `bash scripts/hub-smoke-test.sh`.
- [ ] Commit: `feat: constrain hub projects to portable root`.

### Task 4: Add project-migrate

**Files:**
- Create: `hub-template/ai/skills/project-migrate/SKILL.md`
- Modify: `hub-template/AGENTS.md`
- Modify: `hub-template/CLAUDE.md`
- Modify: `hub-template/ai/architecture.md`
- Modify: `scripts/check-consistency.sh`
- Modify: `scripts/hub-smoke-test.sh`

- [ ] Require a separately confirmed temporary source that is not `/`, home, hub, or projects root; never write it to `allowed-roots.md`.
- [ ] Inventory only direct-child names, excluding `_ai-hub`, backups, archives, symlinks, and unknown folders; do not recurse or read content.
- [ ] Show every source-to-destination mapping, Git status, and collision state before any move.
- [ ] Require each move or displayed batch to be explicitly confirmed. Revalidate, move (never copy), preserve `.git/`, and stop on any failure.
- [ ] Register a moved project only after separate card/registry confirmation and validator success.
- [ ] Add smoke-test fixtures rejecting permanent migration sources, copying, automatic continuation, and unsafe candidates.
- [ ] Commit: `feat: add portable project migration workflow`.

### Task 5: Update docs and review

**Files:**
- Modify: `README.md`
- Modify: `docs/install.md`
- Modify: `docs/prompts.md`
- Modify: `docs/concepts.md`
- Modify: `docs/update-installed-projects.md`

- [ ] Replace all `--root` hub examples with `bash scripts/install.sh --mode hub /path/to/_ai-hub`.
- [ ] Document `_ai-hub/projects/<project>`, independent project repositories, `/projects/` ignore, and separate confirmed migration.
- [ ] Run `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `git diff --check`, and `git status --short`.
- [ ] Request whole-branch review. Fix verified Critical/Important findings and re-run affected tests.
- [ ] Propose `task-finish`; do not move real projects, merge, push, or delete worktrees without explicit confirmation.
