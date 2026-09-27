# Stage 8 — All Modules In modules/, Strict Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** every module lives in `modules/<id>/`, `check-module-boundaries.py --strict` reports 0 and is part of the test run, core joins the "no planning/calendar" strict check.

**Architecture:** Refine the dependency rule (always-installed modules may reference each other), replace required→optional references with two new events and `ai/modules.md` lookups, then move files. Hub target paths never change.

**Tech Stack:** Markdown, bash, Python `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-26-modular-architecture-design.md` → "Stage 8 details" (binding), plus "Stage 4 details" → Events/Boundary check for the existing mechanism.

## Global Constraints

- Repo `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture`, branch `modular-stage-8`.
- Never touch the working Hub (`/Users/zykovsrg/Documents/vibecode/_ai-hub` outside `projects/`). No push.
- Persistent AI-facing text in English. Commit messages in Russian, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Every new check is shown failing on a deliberately broken case before it counts (decision 2026-08-15).
- Any content change to core `architecture.md` bumps `Version:` (currently `2.0` → `2.1`).
- Before deleting any file or folder, `grep` `ai/decisions.md` for it and record the result in the report.
- Git moves use `git mv` so history follows.
- Baseline at branch start (local): check-consistency 0; hub-smoke-test 1 (symlinked /tmp, green in CI); architecture-test 0; assistant-workflows 0; `tests` 184 OK; obsidian 15 OK; planning 8 OK; pytest 39 failed/261 passed (env); boundaries 27 warnings. Nothing may get worse; boundaries must end at 0.
- Test runner: `bash /private/tmp/claude-501/-Users-zykovsrg-Documents-vibecode--ai-hub/2995716d-f91c-4da5-a5c5-323184828f54/scratchpad/runtests.sh <outdir>`.
- Event names exactly: `before-task-close`, `after-project-create`.

---

### Task 1: Dependency rule + strict tests (red)

**Files:** `scripts/check-module-boundaries.py` (allowed set, line ~32), `tests/test_module_boundaries.py`, `tests/test_module_events.py` (`NO_PLANNING_CALENDAR`), `scripts/architecture-test.sh` (last line of `unit()`).

- [ ] Add `"core", "projects", "tasks"` to every module's `allowed` set in `find_violations`. Add a unit test: a fixture module file in optional module A naming a skill of `tasks` → no violation; naming a skill of optional module B not in Depends → violation.
- [ ] `NO_PLANNING_CALENDAR = ["core", "projects", "tasks"]`; remove the stage-7 comment.
- [ ] In `architecture-test.sh` change the boundary call to `--strict`.
- [ ] Run: boundary count drops (expected 9 left: optional-module references); `test_module_events` and `architecture-test.sh` are RED — expected until Task 3. Record counts.
- [ ] Commit `test: строгая проверка границ и ядро без планирования (пока красные)`.

### Task 2: Events `before-task-close` and `after-project-create`

**Files:** `scripts/module_passports.py` (`EVENTS`), `hub-template/ai/skills/hub-task-finish/SKILL.md`, `hub-template/ai/skills/hub-project-create/SKILL.md`, `modules/learning/module.md`, `modules/knowledge/module.md`, `modules/learning/rules.md`, `modules/knowledge/rules.md`, `tests/test_module_events.py`, `tests/test_module_selection.py` (or wherever `ai/modules.md` rendering is tested).

- [ ] Tests first: `hub-task-finish/SKILL.md` contains `` `before-task-close` `` and `ai/modules.md` and no `hub-session-review` / `hub-knowledge-review`; `hub-project-create/SKILL.md` contains `` `after-project-create` `` and no `hub-knowledge-*`; generated `ai/modules.md` with all modules lists learning and knowledge under `before-task-close` and knowledge under `after-project-create`; without learning+knowledge both events show `—`. Run → red.
- [ ] Add both names to `EVENTS`.
- [ ] `hub-task-finish`: replace step 3 (session review) and step 4 (knowledge-review offer) with one step using the same wording pattern as the existing `after-task-write` step: after Done criteria pass and before clearing task context, read `ai/modules.md`; for each `before-task-close` subscriber read its rules file and run its command for this task; a subscriber failure leaves the task open and its context intact; no subscribers → continue. Keep "An improvement suggested by a subscriber waits for user approval and is not a closure blocker."
- [ ] `modules/learning/rules.md` gets `## before-task-close` with the moved session-review text (run `hub-session-review` for the current visible session, save+validate, add `Session review: ai/session-reviews/<file>.md` to the task, reuse on retry, partial history does not block). Passport: `Subscribes: - before-task-close: follow ai/rules/learning.md § before-task-close`.
- [ ] `modules/knowledge/rules.md` gets `## before-task-close` (may offer, never start, `hub-knowledge-review`; declining has no effect) and `## after-project-create` (create the empty scaffold exactly as the current `hub-project-create` text lists it: `knowledge/README.md`, `knowledge/record-template.md`, and the `research/ decisions/ risks/ runbooks/ inbox/` directories; items shown on the same creation preview). Passport subscribes to both. Move scaffold resource files, if `hub-project-create` has them under `resources/`, into the knowledge module's installed paths (keep Hub target paths working; update references).
- [ ] `hub-project-create`: remove knowledge-specific text; add the event step: preview includes subscriber items on the same screen; after the confirmed scaffold, read `ai/modules.md` and run each `after-project-create` subscriber for the new project only.
- [ ] Also update `modules/projects/rules.md` / `modules/tasks/rules.md` / `hub-template/ai/architecture.md` sentences that describe these two flows so no rule is duplicated or stale (bump architecture Version if touched).
- [ ] Run tests; `check-consistency.sh` must still pass (`hub-session-review`, `hub-knowledge-*` must still be named in some rules file — they will be in learning/knowledge rules).
- [ ] Commit `feat: события before-task-close и after-project-create`.

### Task 3: Optional skills by role, text fixes → 0 violations

**Files:** `hub-template/ai/skills/hub-project-router/SKILL.md`, `hub-template/CLAUDE.md`, `hub-template/AGENTS.md`, `hub-template/ai/archiprojects.md`, `hub-template/ai/workflow-observations.md`, `modules/learning/module.md`, `modules/tasks/rules.md`, `scripts/check-workflow-memory.sh`, anything else still reported.

- [ ] Router: the session-review route uses "the learning skill listed under `## Skills` in `ai/modules.md`; if learning is not listed, say session review is not installed". Remove `hub-session-review` by name.
- [ ] `CLAUDE.md`/`AGENTS.md`: the two `hub-workflows` mentions become "the planning skill listed in `ai/modules.md`"; keep both files equal after normalization (check-consistency).
- [ ] `archiprojects.md` template: remove the goals mention. `workflow-observations.md`: remove `hub-workflows` by name (say "the planning module"). Learning passport `Uses if present: planning`. `modules/tasks/rules.md`: remove "calendar" (rephrase). `check-workflow-memory.sh`: allowed now (tasks always installed) — verify.
- [ ] Run `python3 scripts/check-module-boundaries.py --strict` → exit 0, 0 warnings; `tests.test_module_events` green; `bash scripts/architecture-test.sh` green.
- [ ] Seen-failing: temporarily add `` `hub-goal-progress` `` to `hub-template/ai/skills/hub-task-intake/SKILL.md`, run `architecture-test.sh` → fails on strict boundaries; revert.
- [ ] Commit `feat: границы модулей — 0 нарушений`.

### Task 4: Move knowledge, goals, learning into modules/

**Files:** `git mv` each `Installs` source of these three passports from `hub-template/…` or `scripts/…` into `modules/<id>/skills/…`, `modules/<id>/scripts/…`, `modules/<id>/data/…` (follow planning's layout: `skills/`, `scripts/`, data templates under the module root or `data/` — pick one and use it for all three); update passport source paths; update every test/script path that pointed at the old locations (`git grep` each moved path).
- [ ] Before: `git grep -n` each moved path; after: no live reference to an old path outside history files (changelogs, decisions, old specs/plans).
- [ ] Test module tests for these modules, if any are in `tests/`, may stay in `tests/` (do not move tests in this task).
- [ ] `hub_release.py preview` against a temp copy of an installed Hub, or the existing release tests, shows identical target paths (release tests green).
- [ ] Full runner vs baseline. Commit `refactor: knowledge, goals, learning в modules/`.

### Task 5: Move core, projects, tasks; remove hub-template/

**Files:** same approach for core, projects, tasks passports (`CLAUDE.md`, `AGENTS.md`, `.gitignore`, `ai/*.md` templates, `projects/.gitkeep`, skills, scripts). Then `hub-template/` is empty → remove it.
- [ ] grep `ai/decisions.md` for `hub-template` (known hits: lines ~8–24, 85, 317–330, 409 — historical text; the 2026-08-15 skill-naming decision and the stage-7 decision name paths that change: record in report, Task 6 adds a decision that supersedes the paths).
- [ ] Update live references: `scripts/check-consistency.sh` (`hub_rule_files`, `architecture`, skill dir discovery, Source Of Truth needle `hub-template/` → `modules/`), `scripts/hub-smoke-test.sh`, `scripts/install-hub.sh`, `scripts/update-installed-hub.sh`, `scripts/hub_release.py`, all tests, `README.md` Source Of Truth section, `getting-started/`, `AGENTS.md`/`CLAUDE.md` of this repo if they name it. Historical docs untouched.
- [ ] `git grep -n "hub-template"` → only history files remain; list them in the report.
- [ ] Full runner vs baseline; release tests prove identical Hub target paths. Commit `refactor: core, projects, tasks в modules/; hub-template удалён`.

### Task 6: Record

- [ ] Decision `2026-09-27 — Все модули в modules/, строгие границы`: refined dependency rule, two new events, role lookup via `ai/modules.md`, `hub-template/` removed (sources now `modules/<id>/`; amends path mentions in 2026-08-15 and the stage-7 decision).
- [ ] `ai/changelog.md` + root `CHANGELOG.md` (same format as stage 7): boundaries 27 → 0 strict, architecture Version.
- [ ] Commit `docs: итоги этапа 8`.
