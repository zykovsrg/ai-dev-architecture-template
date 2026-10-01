# Modular Architecture Steps 1–2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make this repository the single source of the live Hub again (no Hub-only code, a failing check on drift) and remove dead code.

**Architecture:** Reuse the existing release engine `scripts/hub_release.py`: its `preview()` already marks a managed file that differs from both the incoming and the installed version as `conflict`. A new `drift` subcommand reports those conflicts plus runtime files present in the Hub but absent from the manifest. Hub-only code is copied back here, merged, added to `RUNTIME_SCRIPTS`, then the live Hub is updated through the normal preview/confirm path. Dead code is removed only after a reference check.

**Tech Stack:** Python 3 (`unittest`), Bash, Markdown skills.

**Spec:** `docs/superpowers/specs/2026-09-26-modular-architecture-design.md` (Phases → This task, items 2–3).

## Global Constraints

- Paths: repository `R=/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture`; live Hub `H=/Users/zykovsrg/Documents/vibecode/_ai-hub`.
- Read the live Hub freely; write to it **only** in Task 6, through `scripts/update-installed-hub.sh` preview → user confirmation → apply.
- Calendar-policy code is edited only in `calendar-policy/` and installed via `scripts/sync-calendar-policy.sh` (decision 2026-08-31 in `ai/decisions.md`). Past-event update/delete is intentionally allowed; do not restore that protection.
- If a removed or changed rule looks unexpected, ask the user before reverting it (decision 2026-08-31).
- Commit messages in Russian, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Do not commit `ai/changelog.md` or `ai/future-tasks.md` hunks you did not write (pre-existing uncommitted edits from 2026-09-23).
- Full verification command set ("full suite"):
  ```bash
  cd $R && bash scripts/check-consistency.sh && bash scripts/architecture-test.sh --all && python3 -m unittest discover -s tests -v && bash scripts/apple-calendar-policy-test.sh
  ```

## Known drift (measured 2026-09-26)

`python3 scripts/hub_release.py preview --source $R --hub $H` → 44 keep, 3 replace, 11 conflict.

| Hub path | Situation | Resolution rule |
|---|---|---|
| `ai/skills/hub-workflows/SKILL.md` | Hub-only lines (+6: run `check-all-task-records.sh` after task writes) | take Hub |
| `ai/skills/hub-workflows/resources/day-plan.md` | Hub reworked 2026-09-18 (shorter plan) and 2026-09-21 (`## Синхронизация`); Hub has uncommitted partial-read lines | take Hub (user checkpoint in Task 4) |
| `ai/skills/hub-workflows/resources/evening-review.md` | Hub removed `Сделано`/`Перенос`/`Три главных действия` 2026-09-18, added sync; uncommitted partial-read line | take Hub (user checkpoint in Task 4) |
| `ai/skills/hub-workflows/resources/calendar-context.md` | Hub-only uncommitted partial-read line | take Hub |
| `ai/skills/hub-calendar/SKILL.md` | Template-only partial-read paragraph (8 lines, 2026-09-26) | keep template |
| `ai/skills/hub-calendar/resources/joint-task-change.md` | Hub adds `Событие:` sentence | take Hub |
| `ai/skills/hub-task-intake/SKILL.md` | Hub adds `Событие:` sentence | take Hub |
| `ai/skills/hub-task-intake/resources/task-record-format.md` | Hub adds `Событие:` format | take Hub |
| `ai/skills/hub-session-review/SKILL.md` | Hub +44 / template +13 (2026-09-21 Hub rewrite) | take Hub, then diff template-only lines and keep any rule missing from Hub |
| `ai/skills/hub-session-review/resources/review-template.md` | Hub adds 3 audit lines | take Hub |
| `scripts/task_records.py` | Hub adds `scheduled`/`event_link` parsing (2026-09-21); template has 2026-09-15 heading-warning refactor | take Hub, prove with both test sets |
| `scripts/check-session-review.py` | Hub +9 / template +4 | take Hub, prove with both test sets |
| `scripts/validate-day-plan-output.py` | Hub +1 / template +2; not in release list | take Hub, prove with both test sets; add to release |
| `scripts/calendar_task_sync.py` | Hub-only, no source here | copy; add to release |
| `scripts/calendar-context.py` | identical; not in release list | add to release |
| `tests/*` in Hub | 7 Hub-only tests, 2 differing | move here (Task 3) |

---

### Task 1: `drift` command in the release engine

**Files:**
- Modify: `scripts/hub_release.py` (add `drift()` after `preview()`; add subcommand in `main()`)
- Test: `tests/test_hub_release.py` (new class `DriftTests` at end of file)

**Interfaces:**
- Produces: `drift(source: Path, hub: Path) -> dict` with keys `conflicts: list[str]`, `unmanaged: list[str]` (sorted Hub-relative paths). CLI: `python3 scripts/hub_release.py drift --source <repo> --hub <hub>` prints JSON; exit 0 when both lists are empty, 1 otherwise.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_hub_release.py`; add `drift` to the existing `from scripts.hub_release import ...` line)

```python
class DriftTests(unittest.TestCase):
    def installed_hub(self, root):
        hub = root / "hub"
        hub.mkdir()
        plan = preview(ROOT, hub)
        apply(ROOT, hub, plan["plan_sha256"])
        return hub

    def test_fresh_install_has_no_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = self.installed_hub(Path(tmp))
            self.assertEqual(drift(ROOT, hub), {"conflicts": [], "unmanaged": []})

    def test_locally_edited_managed_file_is_a_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = self.installed_hub(Path(tmp))
            target = hub / "ai/skills/hub-workflows/SKILL.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nlocal edit\n", encoding="utf-8")
            self.assertEqual(drift(ROOT, hub)["conflicts"], ["ai/skills/hub-workflows/SKILL.md"])

    def test_hub_only_runtime_file_is_unmanaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = self.installed_hub(Path(tmp))
            (hub / "scripts/extra_tool.py").write_text("print(1)\n", encoding="utf-8")
            (hub / "scripts/__pycache__").mkdir(exist_ok=True)
            (hub / "scripts/__pycache__/x.cpython-313.pyc").write_bytes(b"\0")
            self.assertEqual(drift(ROOT, hub)["unmanaged"], ["scripts/extra_tool.py"])
```

- [ ] **Step 2: Run to verify failure**

Run: `cd $R && python3 -m unittest tests.test_hub_release.DriftTests -v`
Expected: ImportError / FAIL — `drift` not defined.

- [ ] **Step 3: Implement** (in `scripts/hub_release.py`, below `preview()`)

```python
DRIFT_ROOTS = ("scripts", "ai/skills")


def drift(source, hub):
    payload = preview(source, hub)
    managed = {entry["target"] for entry in payload["manifest"]["files"]}
    conflicts = sorted(row["target"] for row in payload["operations"] if row["action"] == "conflict")
    hub = hub.resolve()
    unmanaged = []
    for name in DRIFT_ROOTS:
        base = hub / name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            target = str(path.relative_to(hub))
            if target not in managed:
                unmanaged.append(target)
    return {"conflicts": conflicts, "unmanaged": unmanaged}
```

In `main()`, register the subcommand next to `preview`:

```python
    drift_command = commands.add_parser("drift")
    drift_command.add_argument("--source", required=True, type=Path)
    drift_command.add_argument("--hub", required=True, type=Path)
```

and handle it before `expected = build_manifest(...)`:

```python
    if args.command == "drift":
        report = drift(args.source, args.hub)
        emit(report)
        return 1 if report["conflicts"] or report["unmanaged"] else 0
```

- [ ] **Step 4: Run tests**

Run: `cd $R && python3 -m unittest tests.test_hub_release -v`
Expected: all PASS.

- [ ] **Step 5: Baseline on the live Hub (read-only)**

Run: `cd $R && python3 scripts/hub_release.py drift --source $R --hub $H; echo "exit $?"`
Expected: exit 1; `conflicts` = the 11 conflict paths from the table; `unmanaged` includes `scripts/calendar_task_sync.py`, `scripts/calendar-context.py`, `scripts/validate-day-plan-output.py`. Save the output in the task handoff; any path not in the table is a new finding — stop and report it.

- [ ] **Step 6: Commit**

```bash
cd $R && git add scripts/hub_release.py tests/test_hub_release.py
git commit -m "feat: проверка расхождений хаба и шаблона"
```

### Task 2: Bring Hub-only scripts into the release

**Files:**
- Create: `scripts/calendar_task_sync.py` (copy of `$H/scripts/calendar_task_sync.py`)
- Modify: `scripts/validate-day-plan-output.py`, `scripts/task_records.py`, `scripts/check-session-review.py` (take Hub versions)
- Modify: `scripts/hub_release.py` (`RUNTIME_SCRIPTS`)
- Test: `tests/test_hub_release.py`

**Interfaces:**
- Consumes: `drift()` from Task 1.
- Produces: `RUNTIME_SCRIPTS` additionally contains `scripts/calendar_task_sync.py`, `scripts/calendar-context.py`, `scripts/validate-day-plan-output.py`.

- [ ] **Step 1: Failing test** (in `ReleaseDecisionTests`)

```python
    def test_release_includes_planning_runtime_scripts(self):
        targets = {entry["target"] for entry in build_manifest(ROOT)["files"]}
        for name in ("scripts/calendar_task_sync.py", "scripts/calendar-context.py",
                     "scripts/validate-day-plan-output.py"):
            self.assertIn(name, targets)
```

Run: `python3 -m unittest tests.test_hub_release -v` → FAIL.

- [ ] **Step 2: Copy Hub versions**

```bash
cd $R
for f in calendar_task_sync.py validate-day-plan-output.py task_records.py check-session-review.py; do cp -p "$H/scripts/$f" "scripts/$f"; done
git diff --stat scripts/
```

- [ ] **Step 3: Recover template-only logic, if any**

For `task_records.py`, `check-session-review.py`, `validate-day-plan-output.py` run `git diff HEAD -- scripts/<file>` and read every removed (`-`) line. Known case: `task_records.py` loses the `if compact: break` early exits; the Hub moved parsing of `Запланировано:`/`Событие:` before the compact skip on purpose. Keep the Hub version unless the full suite in Task 3 fails on a template test; then re-add only the lines that test needs.

- [ ] **Step 4: Register scripts** — edit `RUNTIME_SCRIPTS` in `scripts/hub_release.py`, appending:

```python
    "scripts/calendar_task_sync.py", "scripts/calendar-context.py",
    "scripts/validate-day-plan-output.py",
```

- [ ] **Step 5: Run** `python3 -m unittest tests.test_hub_release -v` → PASS. Full suite is run at the end of Task 3 (Hub tests are needed first).

- [ ] **Step 6: Commit**

```bash
git add scripts/ tests/test_hub_release.py
git commit -m "fix: вернуть в шаблон скрипты планирования из хаба"
```

### Task 3: Move Hub tests here and wire them in

**Files:**
- Create in `tests/`: `test-calendar-task-sync.py`, `test-check-session-review.py`, `test-count-goal-progress.sh`, `test-task-heading-warnings.sh`, `test-task-records-due.py`, `test-task-records-sync-fields.py`, `test-validate-day-plan-output.sh` (copies from `$H/tests/`)
- Modify: `tests/test-check-workflow-memory.sh`, `tests/test-snapshot-calendar.sh` (merge with Hub)
- Modify: `scripts/architecture-test.sh` (`unit()`)

- [ ] **Step 1: Check for duplicates before copying.** The repository already has `tests/test_task_heading_warnings.py` and `tests/test-day-plan-output.sh`. For each Hub test, compare what it covers with the closest local test (`diff`, read both). If a Hub test fully duplicates a local one, skip it; if it adds cases, copy it. Record the decision per file in the commit message.

- [ ] **Step 2: Copy chosen tests and fix paths.** Hub tests locate scripts relative to their own directory; after copying, run each once:

```bash
cd $R && for t in tests/test-*.sh; do bash "$t" || echo "FAIL $t"; done
for t in tests/test-*.py; do python3 "$t" || echo "FAIL $t"; done
```

Fix only path assumptions (e.g. a hard-coded Hub root). Any logic failure means Task 2 lost template logic — go back to Task 2 Step 3.

- [ ] **Step 3: Merge the two differing tests.** For `test-check-workflow-memory.sh` (+146 Hub / +13 here) and `test-snapshot-calendar.sh` (+88 / +18): take the Hub version, then re-add local-only cases that still pass.

- [ ] **Step 4: Wire into `unit()`** in `scripts/architecture-test.sh`, after the existing lines:

```bash
  for test in "$ROOT"/tests/test-*.sh; do bash "$test"; done
  for test in "$ROOT"/tests/test-*.py; do python3 "$test"; done
```

and delete the now-duplicated explicit `bash "$ROOT/tests/test-....sh"` lines above it.

- [ ] **Step 5: Full suite** → all green. Then `git add tests/ scripts/architecture-test.sh && git commit -m "test: перенести тесты хаба в проект архитектуры"`.

### Task 4: Reconcile the 10 skill files

**Files:** the 10 `hub-template/ai/skills/...` paths from the drift table.

- [ ] **Step 1: User checkpoint.** Before editing, tell the user in one short Russian message: the Hub's day plan and evening review are the shortened 2026-09-18 versions with `## Синхронизация`, and the template will take them. Wait for "да". If the user objects, stop and re-plan this task.

- [ ] **Step 2: Copy Hub versions for every "take Hub" row**

```bash
cd $R
for f in hub-workflows/SKILL.md hub-workflows/resources/day-plan.md hub-workflows/resources/evening-review.md \
         hub-workflows/resources/calendar-context.md hub-calendar/resources/joint-task-change.md \
         hub-task-intake/SKILL.md hub-task-intake/resources/task-record-format.md \
         hub-session-review/SKILL.md hub-session-review/resources/review-template.md; do
  cp -p "$H/ai/skills/$f" "hub-template/ai/skills/$f"
done
```

`hub-calendar/SKILL.md` stays as is (template is newer).

- [ ] **Step 3: Recover template-only rules.** `git diff HEAD -- hub-template/ai/skills/` and read every removed line. Expected removals: the old day-plan/evening-review sections (intended) and 13 session-review lines. For session-review, keep a removed rule only if the Hub text has no equivalent; list what you restored in the commit message.

- [ ] **Step 4: Full suite** → green (`check-consistency.sh` validates AGENTS/CLAUDE parity and skill lists; `validate-day-plan-output.py` tests validate the plan format).

- [ ] **Step 5: Drift re-check**: `python3 scripts/hub_release.py drift --source $R --hub $H` → `conflicts` may now list only files whose Hub copy differs from the new template **and** from the installed baseline; for the 10 skill files the Hub content should equal the template except `hub-calendar/SKILL.md` (Hub lacks the partial-read paragraph — resolved by Task 6).

- [ ] **Step 6: Commit** `git add hub-template/ai/skills && git commit -m "fix: выровнять навыки шаблона с хабом"`.

### Task 5: Remove dead code

**Files:** see each step. Before every removal: `grep -rn "<name>" --exclude-dir=.git --exclude-dir=obsidian-vault --exclude-dir=vendor $R`. References inside dated historical docs (`docs/superpowers/plans|specs|research`, `docs/audits`, `archive/`, `ai/session-reviews`, `ai/changelog.md`) stay untouched; any other reference must be removed or updated in the same step.

- [ ] **Step 1: `vendor/apple-calendar-mcp` + `scripts/apple-calendar-upstream-test.sh`.** Confirm `calendar-policy/pyproject.toml` and `scripts/build-calendar-bridge.sh` do not reference `vendor`. `git rm -r vendor scripts/apple-calendar-upstream-test.sh`; fix any live reference (e.g. in `scripts/apple-calendar-policy-test.sh`).
- [ ] **Step 2: Retired standalone updater and its legacy smoke test.** First run `bash scripts/smoke-test.sh; echo $?` and record the result: it drives the retired `update-installed-architecture.sh`, which always exits 2, and CI does not run it. Then `git rm scripts/update-installed-architecture.sh scripts/smoke-test.sh`; in `tests/test_hub_only_distribution.py` replace the test that reads the stub with an assertion that the file is absent; keep the forbidden-string check in `scripts/check-consistency.sh:112`.
- [ ] **Step 3: Legacy Obsidian bridge.** `git rm scripts/install-legacy-hub-obsidian-bridge.sh scripts/legacy-hub-obsidian-bridge-test.sh`.
- [ ] **Step 4: `project_rule_consolidation.py`.** `git rm scripts/project_rule_consolidation.py tests/test_project_rule_consolidation.py`.
- [ ] **Step 5: Stale manifest.** `python3 scripts/hub_release.py check --source . --manifest release/hub-files.json` currently fails and nothing reads the file. `git rm -r release`.
- [ ] **Step 6: Full suite** → green. Commit: `git commit -m "chore: удалить мёртвый код"` (list removed paths in the body).

### Task 6: Update the live Hub

- [ ] **Step 1: Preview** — `bash scripts/update-installed-hub.sh --hub $H --source $R --dry-run`. Expected: `create` for the three planning scripts, `replace`/`keep` elsewhere, **no `conflict`**. If conflicts remain, stop and show them.
- [ ] **Step 2: User confirmation.** Show the user the preview summary and the plan SHA; wait for explicit confirmation.
- [ ] **Step 3: Apply** — `bash scripts/update-installed-hub.sh --hub $H --source $R --apply --confirm-plan <PLAN_SHA256>`.
- [ ] **Step 4: Verify** — `python3 scripts/hub_release.py drift --source $R --hub $H; echo "exit $?"` → exit 0. Run `bash $H/scripts/check-all-task-records.sh --hub $H`.
- [ ] **Step 5: Hub leftovers (separate confirmation each).** Show and ask before: (a) committing the Hub's pending changes; (b) removing `$H/tests/` (now owned by this repository).

### Task 7: Stale references and folder hygiene

- [ ] **Step 1: `template/` references.** Update `docs/file-roles.md`, `docs/concepts.md`, `docs/install.md`, `docs/update.md`, `docs/prompts.md`, and the "Главные папки" list in `ai/project-context.md` so they name `hub-template/`, `calendar-policy/`, `scripts/hub_release.py`, and do not mention removed files. Run `grep -rn "template/" docs/*.md ai/project-context.md` → only `hub-template/` hits remain.
- [ ] **Step 2: One plans/specs folder.** `git mv ai/superpowers/plans/* docs/superpowers/plans/` and `git mv ai/superpowers/specs/* docs/superpowers/specs/`; move `archive/superpowers/*` into `docs/superpowers/archive/`. Leave `.superpowers/sdd/` (tool state) in place.
- [ ] **Step 3: User checkpoint for local-only files.** Ask the user, in one message, about: (a) `ai/skills/` (11 old skills, not in Git, not used by the Hub) — keep, move to `archive/legacy-skills/`, or delete; (b) the `/ai/` line in `.git/info/exclude` that hides new `ai/` files while some are tracked — remove the line or keep. Act only on the answer.
- [ ] **Step 4: Full suite** → green. Commit `docs: убрать устаревшие ссылки и собрать планы в одном месте`.

### Task 8: Close-out

- [ ] Update `ai/current-task.md` (stage, handoff), add a `ai/changelog.md` entry, record in `ai/decisions.md`: "The architecture repository is the only source for Hub runtime files; `hub_release.py drift` must exit 0 after every Hub update."
- [ ] Hand off to `hub-task-finish`.

## Self-review

- Spec coverage: drift sync (Tasks 2–4, 6), drift check (Task 1), release list (Task 2), dead code list from spec Problem section (Task 5: vendor, stub, legacy bridge, rule consolidation, `release/hub-files.json`; Task 7: `template/` refs, plan folders). The `archiproject_contribution` field removal belongs to phase 6 (FT-20260926-003), not here.
- Added beyond the spec, found during planning: Hub-only tests (Task 3) and the dead `scripts/smoke-test.sh` (Task 5 Step 2).
