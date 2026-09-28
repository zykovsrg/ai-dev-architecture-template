# Switchable knowledge/goals/learning + full documentation refresh

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development.

**Goal:** knowledge, goals, learning can be switched off/on like obsidian/planning/calendar; all user-facing documentation matches the modular architecture of stages 1–8.

**Spec:** `docs/superpowers/specs/2026-09-26-modular-architecture-design.md` ("Layout and switching", "Stage 8 details").

## Global Constraints

- Repo `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture`, branch `optional-modules-switch-docs`. No push, never touch the working Hub, no subagents.
- User data is never deleted when a module is switched off: `ai/goals.md`, `ai/goal-log.md`, `ai/workflow-observations.md` (in `MEMORY_FILES` of `scripts/hub_release.py`), anything under `projects/` (knowledge records, session reviews).
- Strict boundaries stay 0 (`python3 scripts/check-module-boundaries.py --strict`). Every new check seen failing first.
- Baseline (local, `python3` = system 3.9 in this session): check-consistency 0; `tests` 190 OK; obsidian 15 OK; planning 8 OK; architecture-test 0 expected; hub-smoke 1 (symlinked /tmp); pytest not installed for 3.9 — run pytest with `/opt/homebrew/bin/python3 -m pytest -q` if available, else note it.
- Commit messages in Russian ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Persistent AI-facing text in English; user docs keep their current language (Russian docs stay Russian, English stay English).
- History is never rewritten: `CHANGELOG.md` old entries, `ai/changelog.md`, `ai/decisions.md` old entries, `docs/superpowers/`, `docs/audits/`.

### Task 1: knowledge, goals, learning switchable

**Files:** `modules/{knowledge,goals,learning}/module.md`; new `tests/test_optional_modules_switch.py` modelled on `tests/test_planning_calendar_switch.py`; `modules/*/rules.md` or skills only if a switch-off leaves a dangling reference.

- [ ] Test first: for each of knowledge, goals, learning — install a Hub (pattern from the planning test), dry-run + apply `--without <id>`: exactly that module's managed files are removed (skills, rules, scripts), user-data files listed above survive unchanged, `ai/modules.md` no longer lists the module or its event subscriptions; then `--with <id>` restores them. Refusals: `--without` on a module that a selected module lists in `Depends:` is refused (check whether any module depends on these; planning only *uses if present* goals/learning — so removal must be allowed with planning installed). Run → red.
- [ ] Set `Switchable: yes` in the three passports. Run → green. Check nothing else in `scripts/hub_release.py`/`update-installed-hub.sh` special-cases the old switchable list (grep `obsidian`, `planning`, `calendar` lists) and extend if needed.
- [ ] Verify with all three removed at once: remaining skills name none of them (strict boundaries guarantee this for sources; also grep the generated installed Hub).
- [ ] Commit `feat: knowledge, goals, learning выключаются`.

### Task 2: Full documentation refresh

**Files:** `README.md`, `getting-started/help.md`, `docs/concepts.md`, `docs/file-roles.md`, `docs/install.md`, `docs/no-github.md`, `docs/prompts.md`, `docs/start-prompts.md`, `docs/uninstall.md`, `docs/update-installed-projects.md`, `docs/update.md`; add a new `CHANGELOG.md` entry (do not edit old ones); this repo's own `AGENTS.md`/`CLAUDE.md` only if they describe the layout.

- [ ] Read every file above in full and check each claim against the code (`modules/*/module.md`, `scripts/`, `.github/workflows/`, generated `ai/modules.md` via `scripts/module_passports.py`). Fix everything stale: paths (`hub-template/`, old `scripts/` locations now in `modules/<id>/scripts/`), the module list (10 modules: core, projects, tasks required; knowledge, goals, learning, calendar, planning, obsidian switchable; release repository-only), dependencies (planning needs calendar; planning uses goals/learning if present), events (`after-task-write`, `before-task-confirmation`, `after-calendar-change`, `before-task-close`, `after-project-create`), `ai/rules/<id>.md`, `ai/modules.md`, architecture.md = core rules only, strict boundary check, how to switch modules on/off and what is never deleted, how to run tests (match CI), Python requirement (system 3.9 works).
- [ ] `docs/update.md` "Модули" section: one table of switchable modules with what switching off removes/keeps and what stops working, then the commands.
- [ ] `docs/file-roles.md`: repository layout by module.
- [ ] Keep each doc's purpose and language; remove duplication between docs by pointing to the one place (same principle as stage 7). Do not invent features.
- [ ] `bash scripts/check-consistency.sh` (it checks README Source Of Truth and active docs) → 0; `git grep -n "hub-template" -- README.md getting-started docs/*.md` → nothing.
- [ ] Commit `docs: полное обновление документации под модульную архитектуру`.

### Task 3: Record

- [ ] Spec: short "Post-stage 8" note in the spec (knowledge/goals/learning switchable; Python 3.9 compatibility requirement for installed scripts, guarded by `tests/test_python39_compat.py`).
- [ ] `ai/decisions.md`: decision `2026-09-28 — knowledge, goals, learning выключаемые; скрипты хаба совместимы с Python 3.9` (newest on top).
- [ ] `ai/changelog.md` entry (newest on top), root `CHANGELOG.md` entry.
- [ ] Commit `docs: итоги — выключаемые модули и документация`.
