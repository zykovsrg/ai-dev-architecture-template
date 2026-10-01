# Archiprojects: Nested Groups and Goals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nested archiproject groups, goals in `ai/goals.md`, a sixth `group` column in the compact project index, a group tree and group-scoped overview/plan, and a one-time data migration script.

**Architecture:** A stdlib Python helper `scripts/archiprojects.py` (projects module) owns parsing and validation of groups and card group fields and prints the tree and members. `check-hub-registry.sh` delegates group validation to it. Goals get their own file and parser in `count-goal-progress.sh` (goals module). `read-compact-task-index.py` gains `--group`. A repository-only migration script rewrites Hub `ai/` data after confirmation.

**Tech Stack:** Python 3 stdlib, bash 3.2, Markdown.

**Spec:** `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`, sections `Archiprojects` and `Stage 6 details`.

## Global Constraints

- Branch `modular-stage-6`; every before/after comparison uses a clean `git worktree` of the branch base.
- Never write to the working Hub `/Users/zykovsrg/Documents/vibecode/_ai-hub`; fixtures only (Hub dir named `_ai-hub` under `/private/tmp`).
- Python stdlib only; bash 3.2 compatible.
- Group rules: optional `parent:`; unknown parent, cycle, depth > 3 (top = 1), or a `kind: goal` entry in `ai/archiprojects.md` is an error.
- Goal fields: `id`, `name`, `status`, `group`, `target`, `unit`, `due`; `group` must be a known group.
- Cards: only `primary_archiproject: <group-id|none>`; `archiproject_contribution` and `related_archiprojects` are removed everywhere (cards, templates, skills, validation). A card that still has them fails validation after migration.
- Any content change to `hub-template/ai/architecture.md` bumps `Version:` (now 1.14 — check the current value).
- New skill/script files follow passports: add each installed file to the owning `modules/<id>/module.md`.
- Every new check is seen failing first; grep `ai/decisions.md` before deleting a file.
- Commits in Russian with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

### Task 1: `scripts/archiprojects.py` and registry validation

**Files:** Create `scripts/archiprojects.py`, `tests/test_archiprojects.py`. Modify `scripts/check-hub-registry.sh` (replace its archiproject parsing/validation and the card contribution/related checks with a call to `python3 "$SCRIPT_DIR/archiprojects.py" validate --hub "$HUB_DIR"`), `hub-template/ai/archiprojects.md` (schema: only the group template with an optional `parent:` line and a sentence that goals live in `ai/goals.md`), `modules/projects/module.md` (install `scripts/archiprojects.py`).

**Interfaces:**
- `parse_groups(path) -> dict[id, {"id","name","status","parent"}]` (heading + fenced YAML blocks; skip template entries whose id contains `<`); raises `ValueError` on a `kind: goal` entry, a duplicate id, or a missing field.
- `validate(hub) -> list[str]` errors: unknown parent, cycle, depth > 3, card `primary_archiproject` not `none` and not a known group, card containing `archiproject_contribution:` or `related_archiprojects:`.
- `members(groups, cards, group_id) -> sorted list[project_id]` for the group and all descendants; cards read from `ai/project-cards/*.md` (`Project ID:` and `primary_archiproject:`), active and inactive alike.
- CLI: `validate --hub H` (prints errors, exit 1 if any, else `archiprojects: ok`), `tree --hub H` (lines `<indent><id> — <name>` with two spaces per depth, then member projects as `<indent>  - <project_id>`, groups and projects sorted), `members --hub H --group ID` (one id per line; unknown group → exit 2).

- [ ] Tests (fixture Hub dirs built in `tempfile.TemporaryDirectory(dir="/private/tmp")`): valid 3-level tree; missing parent; cycle a→b→a; depth 4; goal entry in the file; card with unknown group; card with a dropped field; `members` of a top group includes subgroup projects; `tree` exact text for a small fixture. RED first.
- [ ] Implement; `bash scripts/check-hub-registry.sh <fixture>` still passes on a clean fixture and fails on each broken one (add a shell-level case to an existing registry test if one exists, else to `tests/test_archiprojects.py` via subprocess).
- [ ] Full suite, check-consistency in clean worktree; commit `feat: вложенные группы архипроектов и их проверка`.

### Task 2: Remove the dropped card fields from templates and skills

**Files:** `hub-template/ai/architecture.md` (the card-fields paragraph ~line 64), `hub-template/ai/skills/hub-project-register/SKILL.md` (~line 60), `hub-template/ai/skills/hub-project-create/SKILL.md` (~line 104), any other hit of `archiproject_contribution|related_archiprojects` under `hub-template/`, `modules/*/skills`, `modules/*/rules.md`, `scripts/`, `modules/*/scripts/`, and tests fixtures (e.g. `modules/obsidian/tests/obsidian-projects-kanban-test.sh` card fixture).

- [ ] Add to `tests/test_archiprojects.py` a test that no installed file (all modules' install pairs via `scripts/module_passports.py`) contains `archiproject_contribution` or `related_archiprojects`. RED.
- [ ] Edit: cards declare only `primary_archiproject: <group-id|none>`; wording keeps "a project belongs to exactly one, most specific group; it is also a member of every ancestor group". Bump architecture Version.
- [ ] Obsidian tests still pass (`bash modules/obsidian/tests/obsidian-projects-kanban-test.sh`, `obsidian-task-sync-test.sh`, `python3 -m unittest discover -s modules/obsidian/tests`), with nested-group fixture: add one fixture group with `parent:` and check the generator resolves its name.
- [ ] Full suite; commit `refactor: карточки проектов хранят только группу`.

### Task 3: Goals in `ai/goals.md`

**Files:** Create `hub-template/ai/goals.md` (header text + one template entry with the seven fields); modify `scripts/hub_release.py` `MEMORY_FILES` (add `ai/goals.md`, create-if-missing), `modules/goals/module.md` (install it), `scripts/count-goal-progress.sh` (read goals from `ai/goals.md`; validate `group` with `python3 "$SCRIPT_DIR/archiprojects.py" members --hub H --group <g>` exit status or by parsing groups; unknown group → error), `hub-template/ai/goal-log.md` header text (goal ids come from `ai/goals.md`), `hub-template/ai/skills/hub-goal-progress/SKILL.md` (source file and output shows the goal's group), tests for count-goal-progress (find with `grep -rln count-goal-progress tests modules`).

- [ ] Tests: goals read from `ai/goals.md`; a goal in `ai/archiprojects.md` is no longer read; unknown goal group fails; output includes group. RED first.
- [ ] Implement; full suite; commit `feat: цели в ai/goals.md с привязкой к группе`.

### Task 4: Group column and group-scoped work

**Files:** `scripts/read-compact-project-index.sh` (sixth tab column `group` = card `primary_archiproject`), `scripts/read-compact-task-index.py` (`--group ID`: read task files only for `archiprojects.members`; unknown group → exit 2 with message), docs that say "five fields" (`hub-template/ai/architecture.md` ~94 and ~517, `hub-project-router/SKILL.md` step 1 lists six fields incl. `group`; the router still never opens a project before confirmation), `hub-template/ai/skills/hub-task-overview/SKILL.md` (group request: resolve group id or name via `scripts/archiprojects.py tree`; a group match is not a project confirmation; use `--group`), `modules/planning/skills/hub-workflows/resources/day-plan.md` and `weekly-review.md` (optional group, same filter). Tests for both scripts.

- [ ] Tests: compact project index has 6 columns with the group; `--group` output contains only member projects and a non-member project's task file is not opened (make it unreadable, e.g. chmod 000, and assert success); unknown group exit 2. RED first.
- [ ] Implement; bump architecture Version once; full suite + planning module tests + check-consistency in clean worktree; commit `feat: работа с группой — колонка group и фильтр --group`.

### Task 5: Migration script (repository-only)

**Files:** Create `scripts/migrate-archiprojects-stage6.py`, `tests/test_migrate_archiprojects_stage6.py`; list the script under `modules/release/module.md` `## Repository only`.

**Behaviour:** `--hub H --dry-run|--apply`:
- adds groups `hadassah-promo` (name `Промо`, parent `hadassah`, status active) and `hadassah-seo` (name `SEO`, parent `hadassah`, status active) if missing;
- moves every `kind: goal` entry from `ai/archiprojects.md` to `ai/goals.md` with `group`: `hadassah-promo-32-aug-sep` → `hadassah-promo`, `seo-pages-80-sep` → `hadassah-seo`; any other goal id → error, nothing written;
- sets `primary_archiproject: hadassah-promo` on cards whose project id matches `release-page-*`, `stranitsa-stomatologii`, `stranitsa-vyezdnoy-sluzhby`, `promo-pages`;
- sets `primary_archiproject: hadassah-seo` on cards currently in `hadassah` whose `Name:` or `Purpose:` contains `SEO` (case-insensitive), except those already chosen for promo;
- deletes the lines `archiproject_contribution:` and `related_archiprojects:` from every card;
- dry-run prints every change as `<file>: <old> -> <new>` plus the SEO project list; apply writes each file atomically, then runs `archiprojects.py validate` and reports the result; a second apply changes nothing.
- Touches only `ai/archiprojects.md`, `ai/goals.md`, `ai/project-cards/*.md`.

- [ ] Tests on a fixture copy shaped like the real data (a few promo, SEO, other cards, both goals): dry-run output, apply result, idempotence, unknown goal aborts with no writes, validate passes after apply. RED first.
- [ ] Commit `feat: скрипт разового переноса групп и целей`.

### Task 6: Working Hub, memory, CI (controller only)

- [ ] Final whole-branch review; one fix wave. Push branch, open PR, CI green, ask the user, merge.
- [ ] Hub update dry-run; apply after "да"; `drift` 0.
- [ ] Migration dry-run on the working Hub; show the user the SEO list and the counts; apply after a separate "да"; `check-hub-registry.sh` and `archiprojects.py tree` succeed; commit the Hub; ask before pushing.
- [ ] Decision (supersedes contribution/related parts of 2026-08-24 and 2026-08-28), changelog, handoff; ask before closing.
