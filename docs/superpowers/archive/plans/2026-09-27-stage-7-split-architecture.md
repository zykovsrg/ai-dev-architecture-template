# Stage 7 — Split architecture.md Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `hub-template/ai/architecture.md` keeps only core rules; every module rule lives once in `modules/<id>/rules.md` (installed as `ai/rules/<id>.md`); route-then-confirm lives only in `hub-project-router`.

**Architecture:** Text moves, it is not rewritten. Passports gain `Rules:` + an `Installs` line. Checks that looked for skill names or phrases in `architecture.md` also look in `modules/*/rules.md`.

**Tech Stack:** Markdown, bash, Python `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-26-modular-architecture-design.md` → "Stage 7 details".

## Global Constraints

- Repo: `/Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture`, branch `modular-stage-7`.
- Persistent instructions stay in English; move text verbatim unless a step says otherwise.
- Any change to `hub-template/ai/architecture.md` bumps `Version:` (decision 2026-08-15). Target `Version: 2.0`.
- Every new check must be seen failing on a deliberately broken case before it counts (decision 2026-08-15).
- Do not touch the working Hub (`/Users/zykovsrg/Documents/vibecode/_ai-hub` outside `projects/`).
- Before deleting any file, grep `ai/decisions.md` for it. (This plan deletes no files.)
- Baseline (branch start): check-consistency 0; hub-smoke-test 1 locally (symlinked /tmp, passes in CI); architecture-test 0 (20 tests); assistant-workflows 0; `tests` 180 OK; obsidian 15 OK; planning 8 OK; pytest 39 failed/257 passed locally (env); boundaries 55 warnings. Results must not get worse.
- Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Section map (current `hub-template/ai/architecture.md`, v1.17)

| Section (line) | Goes to |
|---|---|
| Purpose (5) | core — keep |
| Rule Precedence (13) | core — keep |
| Simplicity, Evidence… (31) | core — keep |
| Ownership And Registry (45) | `modules/projects/rules.md`; the two goal bullets (`ai/goals.md`, `ai/goal-log.md`) → `modules/goals/rules.md` |
| Local Router (79) | delete; replace with one pointer line in core (see Task 3). Already fully in `hub-project-router/SKILL.md`. Keep the bullet "A remembered active project is not a confirmation" only if absent from the router skill (it is present — drop). |
| Project Creation And Registration (117) | projects |
| Existing Project Migration (134) | projects |
| Repository Provisioning (154) | projects |
| Confirmation And Confidence (165) | core — keep |
| Project Switches And Task Switches (180) | first paragraph → projects; second paragraph → tasks |
| Hub-Managed Project Flow (194) | tasks; the `hub-session-review` bullet → learning; the two `hub-knowledge-*` bullets → knowledge |
| Module Rules (226) | core — keep |
| Optional Project Knowledge (233) | knowledge |
| Information Updates (268) | first two paragraphs → core (mode-based write permissions are core); last paragraph (`hub-info-update`, capture) → knowledge |
| Proposal-Only Plans… (295, empty heading) | delete |
| Guarded Apple Calendar (297–421) | paragraphs 1–2 (lines 299–312) → calendar. Everything from line 314 to 421 → `modules/planning/rules.md` under `## Plans and reviews`, but for each paragraph first grep `modules/planning/skills/hub-workflows/` and `modules/planning/rules.md`; if the same rule is already stated there, drop the paragraph. Replace the stale name `hub-workflows skill for day-plan…` sentence only if still accurate. Must keep somewhere the phrases `Calendar events never prove completion` and `exact canonical task-record diff`. |
| Goal Progress (423) | goals |
| Self-Learning Workflows (438) | learning (snapshot sentence: keep in learning, it names `scripts/snapshot-calendar.sh` — allowed because learning's rules are text; if boundary check warns, move that sentence to planning) |
| Cross-Project Signals (455) | projects |
| Project-local Router (471) | projects |
| Installation And Updates (485) | core — keep |
| Secret And Privacy Boundary (500) | core — keep |
| Context-Loading Budget (511) | core — keep; item 2 shrinks to one line pointing at `hub-project-router` |

---

### Task 1: Failing checks for the split

**Files:**
- Create: `tests/test_rules_split.py`
- Modify: `scripts/check-consistency.sh` (line with `hub_rule_files=`)

**Interfaces:**
- Produces: test class `RulesSplitTests`; `hub_rule_files` includes `modules/*/rules.md`.

- [ ] **Step 1: Write the test**

```python
import re
import unittest
from pathlib import Path

from scripts.module_passports import install_pairs, load_passports

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "hub-template/ai/architecture.md"
MODULE_HEADINGS = {
    "## Ownership And Registry", "## Local Router", "## Project Creation And Registration",
    "## Existing Project Migration", "## Repository Provisioning",
    "## Project Switches And Task Switches", "## Hub-Managed Project Flow",
    "## Optional Project Knowledge", "## Proposal-Only Plans, Reviews, And Capture",
    "## Guarded Apple Calendar", "## Goal Progress", "## Self-Learning Workflows",
    "## Cross-Project Signals", "## Project-local Router",
}
WITH_RULES = ["projects", "tasks", "knowledge", "goals", "learning", "calendar", "planning", "obsidian"]


class RulesSplitTests(unittest.TestCase):
    def test_core_has_no_module_sections(self):
        headings = {l.strip() for l in ARCH.read_text(encoding="utf-8").splitlines() if l.startswith("## ")}
        self.assertEqual(sorted(headings & MODULE_HEADINGS), [])

    def test_core_version_is_2(self):
        self.assertIn("Version: 2.0", ARCH.read_text(encoding="utf-8"))

    def test_each_module_rules_file_exists_and_installs(self):
        passports = load_passports(ROOT)
        for module_id in WITH_RULES:
            self.assertEqual(passports[module_id].rules, f"ai/rules/{module_id}.md", module_id)
            self.assertTrue((ROOT / f"modules/{module_id}/rules.md").is_file(), module_id)
            targets = [dst for _, dst in install_pairs(ROOT, passports, [module_id])]
            self.assertIn(f"ai/rules/{module_id}.md", [str(t) for t in targets], module_id)

    def test_route_then_confirm_only_in_router(self):
        phrase = re.compile(r"read-compact-project-index\.sh")
        for rel in ("hub-template/ai/architecture.md", "hub-template/CLAUDE.md", "hub-template/AGENTS.md"):
            hits = phrase.findall((ROOT / rel).read_text(encoding="utf-8"))
            self.assertLessEqual(len(hits), 1, rel)


if __name__ == "__main__":
    unittest.main()
```

Note: check the exact return type of `install_pairs` in `scripts/module_passports.py` and adapt `targets` comparison (it may yield `(source, target)` strings or Paths).

- [ ] **Step 2: Run, expect FAIL**

Run: `python3 -m unittest tests.test_rules_split -v`
Expected: failures in all four tests (module headings present, Version 1.17, rules missing, index script named in several places).

- [ ] **Step 3: Extend `hub_rule_files`**

In `scripts/check-consistency.sh` replace
`hub_rule_files="hub-template/AGENTS.md hub-template/CLAUDE.md hub-template/ai/architecture.md"`
with
`hub_rule_files="hub-template/AGENTS.md hub-template/CLAUDE.md hub-template/ai/architecture.md $(ls modules/*/rules.md 2>/dev/null | tr '\n' ' ')"`
Run `bash scripts/check-consistency.sh` → still exit 0.

- [ ] **Step 4: Commit** — `test: проверки разделения architecture.md (пока красные)`

### Task 2: Module rules files and passports

**Files:**
- Create: `modules/{projects,tasks,knowledge,goals,learning,calendar}/rules.md`
- Modify: `modules/planning/rules.md` (append `## Plans and reviews`)
- Modify: `modules/{projects,tasks,knowledge,goals,learning,calendar}/module.md`

- [ ] **Step 1:** Create each rules file with header `# <Module> Module Rules` and the sections from the Section map, copied verbatim with their `##` headings. For planning, apply the grep-before-copy rule from the map and list in the commit message which paragraphs were dropped as duplicates and where they already live.
- [ ] **Step 2:** In each of the six passports set `Rules: ai/rules/<id>.md` and add under `## Installs`: `- modules/<id>/rules.md -> ai/rules/<id>.md`.
- [ ] **Step 3:** Run `python3 -m unittest tests.test_rules_split -v` → `test_each_module_rules_file_exists_and_installs` passes; `python3 -m unittest tests.test_module_passports tests.test_module_selection -v` → OK. `python3 scripts/check-module-boundaries.py | tail -1` → not more than 55 warnings; if new warnings appear, move the offending sentence to the module that owns the named file.
- [ ] **Step 4: Commit** — `feat: правила модулей в modules/<id>/rules.md`

### Task 3: Core architecture.md, entry files, one-line pointers

**Files:**
- Modify: `hub-template/ai/architecture.md`, `hub-template/CLAUDE.md`, `hub-template/AGENTS.md`
- Modify: `modules/planning/tests/test_hub_workflows_progressive.py:108-111`, `tests/test_live_hub_merge.py:17-22`
- Modify: every `SKILL.md` of projects, tasks, knowledge, goals, learning, calendar (paths from their passports)

- [ ] **Step 1:** Delete from `architecture.md` all sections marked "not core" in the map. Set `Version: 2.0`. Add under `## Module Rules`: "Project routing (route first, then confirm) is defined only in `hub-project-router`." Context-Loading Budget item 2 becomes: "2. For an unconfirmed project-specific request: follow `hub-project-router`." Keep the paragraph from Information Updates marked core under a heading `## Information Updates`.
- [ ] **Step 2:** In `CLAUDE.md` and `AGENTS.md` replace the two lines "Before reading a project, show…" and "Before confirmation, use only compact discovery…" with one line: "- Project routing and confirmation follow `hub-project-router` only; never read a project before its explicit confirmation." Keep both files identical after tool-name normalization (check-consistency verifies).
- [ ] **Step 3:** Add to each module skill, right after the first heading paragraph, one line: "Module rules: `ai/rules/<id>.md`." Do not add it to `hub-project-router` (core).
- [ ] **Step 4:** Point the two phrase tests at their new files: progressive test reads `modules/planning/rules.md`; live-hub-merge test reads `modules/goals/rules.md` for `## Goal Progress`, `modules/learning/rules.md` for `## Self-Learning Workflows`, `hub-session-review`, `snapshot-calendar.sh` (or planning if moved in Task 2).
- [ ] **Step 5:** Run the full suite (`bash <scratchpad>/runtests.sh <scratchpad>/after`) and compare to baseline. `tests.test_rules_split` fully green. `check-consistency` 0 — `[hub skill naming]` must pass through `modules/*/rules.md`.
- [ ] **Step 6: Prove the naming check fails:** temporarily remove `` `hub-goal-progress` `` from `modules/goals/rules.md`, run `bash scripts/check-consistency.sh` → FAIL on hub skill naming, restore.
- [ ] **Step 7: Commit** — `feat: architecture.md 2.0 — только ядро`

### Task 4: Measure, record, decide

**Files:**
- Modify: `ai/decisions.md`, `ai/changelog.md`, `CHANGELOG.md` (if it records template versions)

- [ ] **Step 1:** Measure: `git show main:hub-template/ai/architecture.md | wc -c` vs `wc -c hub-template/ai/architecture.md`; plus `CLAUDE.md` and `hub-project-router/SKILL.md` before/after. Typical project session = entry + router + architecture.
- [ ] **Step 2:** Add decision `2026-09-27 — Правила модулей живут в ai/rules/<id>.md`: amends 2026-08-15 — a skill may be named in `modules/*/rules.md`; route-then-confirm only in `hub-project-router`.
- [ ] **Step 3:** Changelog entry with the measured numbers and the dropped planning duplicates.
- [ ] **Step 4: Commit** — `docs: итоги этапа 7`

### Task 5: PR and CI

- [ ] Push `modular-stage-7`, open PR to `main`, wait for green CI; merge only after green. Then (only after the user's "да") update the working Hub via the normal preview → confirm flow and check `python3 scripts/hub_release.py drift` exit 0.
