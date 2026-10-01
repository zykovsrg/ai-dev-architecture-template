# Planning and Calendar Modules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Planning and calendar become switchable modules under `modules/`; task skills reach them only through events; the calendar server is calendar-only; capture and the task overview work without planning.

**Architecture:** Reuse stage 4 machinery (`scripts/module_passports.py`, `scripts/hub_release.py`, `ai/modules.md`, updater `--with/--without`). Add the event `after-calendar-change` and a per-module skills list to `ai/modules.md`. Split `hub-workflows` into a tasks skill `hub-task-overview` (capture, overview, shared personal-assistant contract) and planning's `hub-workflows` (day plan, reviews). Move planning and calendar files into `modules/`. The calendar server is installed by `sync-calendar-policy.sh`, so the updater calls it (install or new `--remove`) when calendar is switched.

**Tech Stack:** Python 3 stdlib (+ the existing calendar-policy package with pytest), bash 3.2-compatible shell, Markdown skills.

**Spec:** `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`, section `Stage 5 details` (and `Stage 4 details` for the machinery).

## Global Constraints

- Branch `modular-stage-5` in `projects/ai-dev-architecture`; base commit is the branch point. **Every before/after comparison of tests or checks uses a clean `git worktree` of the base commit, not the previous task's HEAD.**
- Never write to the working Hub `/Users/zykovsrg/Documents/vibecode/_ai-hub`; use fixture Hubs under `/private/tmp` (the directory must be named `_ai-hub`; macOS `/var` is a symlink).
- Python stdlib only for scripts; bash 3.2 (`${ARR[@]+"${ARR[@]}"}` for possibly empty arrays).
- Hub targets of moved files do not change (skills in `ai/skills/`, scripts in `scripts/`, rules in `ai/rules/<id>.md`).
- Any content change to `hub-template/ai/architecture.md` bumps `Version:` (now `1.13`; bump once per task that changes it).
- Every new check is seen failing on a deliberately broken case first.
- Before deleting any file, grep `ai/decisions.md` for its name; report hits.
- A skill folder added under an installed path must be named in backticks in `hub-template/CLAUDE.md`, `hub-template/AGENTS.md`, or `hub-template/ai/architecture.md` (decision 2026-08-15, enforced by `scripts/check-consistency.sh`).
- User data is never deleted: `.local/apple-calendar/allowlist.json`, `ai/tmp/calendar-snapshots/`, `ai/tmp/workflow-friction/`, the vault, `projects/`.
- Commit messages in Russian, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

---

### Task 1: Event and passport plumbing

**Files:** Modify `scripts/module_passports.py`, `modules/planning/module.md`, `modules/calendar/module.md`, `tests/test_module_passports.py`.

**Interfaces:**
- Produces: `EVENTS = ("after-task-write", "before-task-confirmation", "after-calendar-change")`. `render_modules_md` output adds `## Skills` after `## Modules`: one line `- <module>: \`<skill>\`, \`<skill>\`` per selected module that installs skills (skill = folder name under target `ai/skills/`), sorted; modules without skills are omitted. It takes `root` to expand directories: new signature `render_modules_md(passports, selected, root=None)`; when `root` is None, skills come from literal install targets only. Update the caller in `scripts/hub_release.py` (`build_manifest`) to pass `root`.
- planning and calendar: `Switchable: yes`.

- [ ] Step 1: Tests first in `tests/test_module_passports.py`:
  - `test_after_calendar_change_is_a_known_event` (parse a passport subscribing to it);
  - `test_modules_md_lists_skills` (fixture with `- modules/demo/skills/ -> ai/skills/` and files `modules/demo/skills/hub-demo/SKILL.md`, `.../hub-demo/resources/x.md`; expect the line `` - demo: `hub-demo` `` under `## Skills`);
  - change `test_only_obsidian_is_switchable` to expect `{"obsidian", "planning", "calendar"}` (rename to `test_switchable_modules`).
- [ ] Step 2: RED, implement, GREEN; full suite `python3 -m unittest discover -s tests -p 'test_*.py'`.
- [ ] Step 3: Commit `feat: событие after-calendar-change и список навыков в ai/modules.md`.

---

### Task 2: `hub-task-overview` (tasks) split from `hub-workflows`; router via `ai/modules.md`

**Files:**
- Create `hub-template/ai/skills/hub-task-overview/SKILL.md`, move `hub-template/ai/skills/hub-workflows/resources/capture.md` → `hub-template/ai/skills/hub-task-overview/resources/capture.md` (`git mv`).
- Modify `hub-template/ai/skills/hub-workflows/SKILL.md`, `hub-template/ai/skills/hub-project-router/SKILL.md`, `hub-template/CLAUDE.md`, `hub-template/AGENTS.md`, `hub-template/ai/architecture.md` (only where it names routing of capture/overview), `modules/tasks/module.md`, tests that assert the moved text (find with `grep -rn "capture\|Personal-assistant scope\|Proposal envelope" tests scripts/*test*.sh scripts/check-consistency.sh`).

**Content rules:**
- `hub-task-overview/SKILL.md` (frontmatter like other skills: `name`, `type: worker`, `description`). It owns, moved verbatim from `hub-workflows/SKILL.md`: `## Personal-assistant scope`, `## Canonical inputs and ranking`, `## Proposal envelope`, `## Confirmation boundary`, and the compact-index/warning rules. It handles `capture` (→ `resources/capture.md`) and the cross-project overview (overdue, blocked, "что горит"; read-only output with canonical `source_path` citations, then optional proposals).
- `hub-workflows/SKILL.md` keeps day plan, evening and weekly review, `## Fixed sequence`, learning lifecycle, calendar-read rules, and replaces each moved section with one line: `Use the personal-assistant contract in \`hub-task-overview\` (scope, inputs, proposal envelope, confirmation boundary).` Its dispatch list drops `capture`.
- Router: capture and overview → `hub-task-overview`; day plan, evening/weekly review → "the planning skill listed under `## Skills` in `ai/modules.md`; if planning is not listed, say planning is not installed and do not improvise a plan". Keep the day-plan phrase list and the six-section day-plan requirement text, but refer to "the planning skill" instead of naming `hub-workflows`.
- `hub-template/CLAUDE.md` / `AGENTS.md`: "Personal-assistant requests use `hub-workflows`" → "Personal-assistant requests go through `hub-project-router`; capture and task overviews use `hub-task-overview`, plans and reviews use the planning skill listed in `ai/modules.md`." Keep the day-plan format line. Both files must stay identical in this section (existing tests compare them).
- `modules/tasks/module.md` installs `hub-template/ai/skills/hub-task-overview/ -> ai/skills/hub-task-overview/`.

- [ ] Step 1: Add `tests/test_task_overview_split.py`:
  - `hub-task-overview/SKILL.md` contains `## Proposal envelope` and `resources/capture.md`;
  - `hub-workflows/SKILL.md` does not contain `## Proposal envelope` and contains `` `hub-task-overview` ``;
  - router contains `` `hub-task-overview` `` and `ai/modules.md`;
  - the tasks passport installs `hub-task-overview`.
  RED.
- [ ] Step 2: Edit; GREEN; full suite; `bash scripts/check-consistency.sh` in a clean worktree of HEAD shows no MISMATCH (compare with base worktree).
- [ ] Step 3: Commit `feat: сбор и обзор задач — отдельный навык задач hub-task-overview`.

---

### Task 3: `before-task-confirmation`; planning rules take the task↔calendar sync

**Files:** Create `modules/planning/rules.md`. Modify the three task skills, `hub-template/ai/skills/hub-task-intake/resources/task-record-format.md` only if it tells task skills to build calendar previews, `modules/planning/module.md`, tests (`tests/test_module_events.py` extension). Move `hub-template/ai/skills/hub-calendar/resources/joint-task-change.md` content into `modules/planning/rules.md` (section `## Joint task and calendar change`) and delete the resource file (grep decisions first; update the calendar passport and any reference).

**Content rules:**
- In `hub-task-intake`, `hub-task-switch`, `hub-task-finish` replace the whole `## Calendar sync for dated tasks` section with:

```markdown
## Confirmation extensions

Before asking the user to confirm a task write, run the
`before-task-confirmation` event: read `<hub>/ai/modules.md`; each subscriber
listed under `before-task-confirmation` may add its own items to the same
confirmation screen by following its rules file. One confirmation approves
exactly the shown set. If a subscriber cannot build its part, say which one and
why, apply nothing, and ask again. With no subscribers, confirm the task write
alone.
```

- `modules/planning/rules.md` (`# Planning Module Rules`): `## before-task-confirmation` = the removed calendar-sync text verbatim (schedule fields, allowlisted calendars via `hub-calendar`, title form, preview contents, create/update/delete rules, `Событие:` link line from `task-record-format.md`, joint confirmation, failure handling); `## Joint task and calendar change` = the former resource; `## after-calendar-change` = the snapshot rule from `hub-calendar` "Snapshot after a change" (Task 4 removes it there).
- planning passport: `Rules: ai/rules/planning.md`; installs `modules/planning/rules.md -> ai/rules/planning.md`; `## Subscribes`: `- before-task-confirmation: follow ai/rules/planning.md § before-task-confirmation` and `- after-calendar-change: follow ai/rules/planning.md § after-calendar-change`.
- Extend `tests/test_module_events.py`: `NO_PLANNING_CALENDAR = ["core", "projects", "tasks"]` — their installed files contain none of `hub-calendar`, `hub-workflows`, `preview_change`, `apply_change`, `read_events`, `snapshot-calendar.sh`, `calendar_task_sync.py`, `Apple Calendar` (case-insensitive for the last); task skills contain `` `before-task-confirmation` ``. Hits in `hub-template/ai/architecture.md`, `AGENTS.md`, `CLAUDE.md` (core) that are stage-7 material: move each such sentence into the owning module's rules file if it is a planning/calendar rule, otherwise replace the name with a generic reference ("the planning module", "the calendar module"). Report every change. RED first.
- [ ] Steps: test RED → edits → GREEN → full suite → check-consistency in clean worktree → commit `feat: навыки задач вызывают планирование через событие before-task-confirmation`.

---

### Task 4: Calendar server and `hub-calendar` become calendar-only

**Files:** Delete `calendar-policy/src/hub_calendar_policy/evening_review.py`, `calendar-policy/tests/test_evening_review.py` (grep decisions first). Modify `server.py`, `mcp_server.py`, `calendar-policy/tests/test_server.py`, `test_mcp_surface.py`, `hub-template/ai/skills/hub-calendar/SKILL.md`, `hub-template/ai/skills/hub-workflows/SKILL.md`, `hub-workflows/resources/evening-review.md`, `tests/test_hub_workflows_progressive.py`, `docs/prompts.md`, `modules/calendar/module.md`.

**Content rules:**
- Server: remove `prepare_evening_review` from `tool_names`, the method, the MCP registration, and the `hub_root` constructor argument if nothing else uses it (keep the entrypoint accepting an unused `HUB_ROOT` env var without error). MCP surface test asserts exactly the remaining tools and that `prepare_evening_review` is absent.
- `hub-calendar/SKILL.md`: drop `prepare_evening_review` from the partial-read paragraph; replace the merged-gate exception naming task skills/`hub-workflows` with: "One exception keeps the preview but merges the gate: another installed module may show this complete preview together with its own diff on one screen, and one confirmation approves exactly that shown pair." Keep the rest of that paragraph's safeguards. Replace `## Snapshot after a change` with `## after-calendar-change`: "After a successful `apply_change`, run the `after-calendar-change` event: read `<hub>/ai/modules.md` and follow each subscriber's rules with the affected calendar ID and date. A subscriber failure is reported and never undoes the applied change." Remove the sentence about snapshot/day-plan cache exceptions or make it generic ("caches defined by an installed subscriber").
- `evening-review.md`: calendar input = metadata then `read_events` for the day (allowed IDs); if complete, pipe `HH:MM|HH:MM|<title>|<calendar>` lines to `bash scripts/snapshot-calendar.sh --hub <hub> --at <date>-<HHMM>`; prior snapshots via `bash scripts/snapshot-calendar.sh --hub <hub> --list --day <date>`; pending friction via `python3 scripts/workflow_friction.py list ...` only when `learning` is listed in `ai/modules.md` (check the real CLI with `python3 scripts/workflow_friction.py --help`). `hub-workflows/SKILL.md` dispatch line no longer says "begins with `prepare_evening_review`".
- [ ] Steps: tests RED (surface test, progressive test expectations) → edits → GREEN: `python3 -m pip install -e ./calendar-policy` if needed, `python3 -m pytest -q calendar-policy`, full unittest suite, check-consistency in clean worktree → commit `refactor: сервер календаря — только календарь, вечерний обзор берёт копии у планирования`.

---

### Task 5: Move planning and calendar files into `modules/`

**Files (`git mv`):**
- `hub-template/ai/skills/hub-workflows/` → `modules/planning/skills/hub-workflows/`; `scripts/snapshot-calendar.sh`, `scripts/calendar-context.py`, `scripts/calendar_task_sync.py`, `scripts/validate-day-plan-output.py` → `modules/planning/scripts/`; planning tests (`tests/test-calendar-context.sh`, `tests/test-calendar-task-sync.py`, `tests/test-day-plan-output.sh`, `tests/test-snapshot-calendar.sh`, `tests/test-validate-day-plan-output.sh`, `tests/test_hub_workflows_progressive.py`, and any other test only exercising these) → `modules/planning/tests/`.
- `hub-template/ai/skills/hub-calendar/` → `modules/calendar/skills/hub-calendar/`; `calendar-policy/` → `modules/calendar/policy/`; `scripts/sync-calendar-policy.sh`, `scripts/build-calendar-bridge.sh`, `scripts/grant-calendar-access.sh`, `scripts/apple-calendar-bridge-test.sh`, `scripts/apple-calendar-policy-test.sh`, `scripts/calendar-policy-install-test.sh` → `modules/calendar/scripts/` (tests may go to `modules/calendar/tests/`).
- `hub-template/ai/workflow-context.md` stays (memory file, create-if-missing policy keyed by target).

**Rules:**
- Passports: `- modules/planning/skills/ -> ai/skills/`, `- modules/planning/scripts/<file> -> scripts/<file>` (list files, not the directory, so tests stay repository-only), `## Repository only` lists tests; same for calendar (`modules/calendar/policy/` repository-only).
- Scripts that locate helpers next to themselves (`source "$SCRIPT_DIR/lib/calendar-date.sh"`, `task_records.py`) keep working in the Hub layout; repository tests stage a Hub-layout directory like `modules/obsidian/tests/stage-scripts.sh` (create `modules/planning/tests/stage-scripts.sh`).
- `sync-calendar-policy.sh` finds `build-calendar-bridge.sh` beside itself and `POLICY_SRC` at `$SOURCE_ROOT/modules/calendar/policy`.
- Update every test that reads moved files by path (e.g. `tests/test_task_overview_split.py`, `tests/test_module_events.py`, `tests/test_live_hub_merge.py`) to the new paths.
- Update `scripts/architecture-test.sh` (unit + integration discover the moved tests), `.github/workflows/hub-architecture-tests.yml` (`pip install -e ./modules/calendar/policy`, pytest path, `discover -s modules/planning/tests`), `scripts/check-consistency.sh` path references, `docs/*.md` user paths (not dated history).
- [ ] Steps: record base-worktree outputs of `bash scripts/architecture-test.sh --unit`, `--integration`, `check-consistency.sh`, `python3 -m pytest -q` → moves → same commands; identical results except known local-only `hub-smoke-test.sh` → `python3 scripts/hub_release.py build --source .` target list identical to base (compare sorted targets) → commit `refactor: планирование и календарь переехали в modules/`.

---

### Task 6: Switching calendar and planning in the updater

**Files:** Modify `modules/calendar/scripts/sync-calendar-policy.sh`, `scripts/update-installed-hub.sh`, `docs/update.md`. Test `tests/test_planning_calendar_switch.py`.

**Behavior:**
- `sync-calendar-policy.sh --remove --hub H [--dry-run]`: lists then deletes `H/tools/apple-calendar-policy` and removes only the `hub_calendar` key from `H/.mcp.json` (Python stdlib JSON rewrite preserving other servers; delete nothing else; keep `.local/apple-calendar/` and snapshots). Install mode additionally adds the `hub_calendar` entry (same shape as today's working Hub `.mcp.json`, paths under `H`) when missing, and never overwrites an existing entry.
- `update-installed-hub.sh`: after computing the plan, if calendar leaves the selection, `print_plan` prints `Extra step: remove calendar server (tools/apple-calendar-policy, .mcp.json hub_calendar)`; if calendar joins, `Extra step: install calendar server`. On `--apply` (same confirmed plan) run `bash "$SOURCE_REPO_ROOT/modules/calendar/scripts/sync-calendar-policy.sh" --source "$SOURCE_REPO_ROOT" --hub "$HUB_DIR"` with `--remove` or without, after `hub_release.py apply` succeeds. On non-macOS the install skips the bridge build as today. Tests set `HUB_CALENDAR_SKIP_BRIDGE=1` if the bridge build must be skipped on macOS fixtures — add that switch to `sync-calendar-policy.sh` only if needed and document it.
- Test (fixture Hub from `install-hub.sh` in `/private/tmp/.../_ai-hub`, then `sync-calendar-policy.sh` install with the skip switch): `--without planning --without calendar` dry-run lists removal of `ai/skills/hub-workflows/...`, `ai/skills/hub-calendar/...`, planning scripts, `ai/rules/planning.md`, and the extra step; apply; assert those are gone, `tools/apple-calendar-policy` gone, `.mcp.json` has no `hub_calendar` but keeps a fixture `other` server; allowlist and a fixture snapshot file unchanged; `ai/modules.md` has no `before-task-confirmation` subscriber; `hub-task-intake/SKILL.md` still present; drift exit 0. Then `--with planning --with calendar` restores files, server dir and `.mcp.json` entry. `--without calendar` alone is refused (planning depends on it). RED first.
- [ ] Steps: RED → implement → GREEN; full suite; `bash tests/test_hub_update_check.sh`; commit `feat: выключение планирования и календаря при обновлении хаба`.

---

### Task 7: Working Hub, memory, CI (controller only)

- [ ] Final whole-branch review; one fix wave.
- [ ] Push the branch `modular-stage-5`; wait for its CI run to be green; then ask the user and merge to `main`, push.
- [ ] Hub dry-run without flags (planning and calendar stay selected): show the list; apply after the user's "да"; run `sync-calendar-policy.sh` refresh (included if the updater does it; otherwise run it explicitly after confirmation).
- [ ] Verify: `drift` exit 0; `check-all-task-records.sh --hub` OK; `ai/modules.md` lists planning subscribers; the running `hub_calendar` MCP needs a new session — tell the user.
- [ ] Commit the Hub, ask before pushing `personal-ai-hub`. Decision + changelog + handoff in project memory; ask before closing.
