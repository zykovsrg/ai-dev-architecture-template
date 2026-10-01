# Module Passports and Obsidian Switch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every module has a passport, the release manifest is built from passports with a persisted module selection and a generated `ai/modules.md`, a boundary check runs in warning mode, and Obsidian becomes the first module that can be switched off (then switched off in the working Hub).

**Architecture:** A new stdlib-only parser (`scripts/module_passports.py`) reads `modules/<id>/module.md`. `scripts/hub_release.py` asks it for install pairs of the selected modules instead of walking `hub-template/` plus `RUNTIME_SCRIPTS`, stores the selection in the manifest (which is saved as `installed.json`), and adds a generated managed file `ai/modules.md`. Task skills stop calling Obsidian and instead fire the `after-task-write` event through `ai/modules.md`. Obsidian files move into `modules/obsidian/`.

**Tech Stack:** Python 3 stdlib (`unittest`), bash 3.2-compatible shell (macOS), Markdown.

**Spec:** `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`, section `Stage 4 details`.

## Global Constraints

- Work on branch `modular-stage-4` in `projects/ai-dev-architecture`; the working Hub is `/Users/zykovsrg/Documents/vibecode/_ai-hub`.
- Python: stdlib only. Shell: must run on macOS bash 3.2 (`set -u` with empty arrays needs `${ARR[@]+"${ARR[@]}"}`).
- The Hub runtime layout does not change: skills in `ai/skills/`, scripts in `scripts/`. New Hub paths: `ai/modules.md`, `ai/rules/<id>.md`.
- Any content change to `hub-template/ai/architecture.md` bumps its `Version:` (currently `1.12` → `1.13`).
- Every new check must be seen failing on a deliberately broken case before it counts (decision 2026-08-15).
- Before deleting any file, search `ai/decisions.md` for its name and report hits.
- Never touch `projects/ai-dev-architecture/obsidian-vault`, anything under `/projects/` or `.local/` (except release metadata written by `hub_release.py apply`).
- The working Hub changes only through `scripts/update-installed-hub.sh` preview → user confirmation → apply; afterwards `python3 scripts/hub_release.py drift --source . --hub <hub>` must exit 0.
- Commit messages in Russian, ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Module ownership (used by Task 1)

| Module | Installs (source → Hub target) | Repository only |
|---|---|---|
| core | `hub-template/.gitignore`, `AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, `ai/allowed-roots.md`, `ai/active-project.md`, `ai/archive/.gitkeep`, `projects/.gitkeep`, skill `hub-project-router/`; `scripts/check-hub-registry.sh`, `scripts/read-compact-project-index.sh` | — |
| projects | `hub-template/ai/project-registry.md`, `ai/project-cards/.gitkeep`, `ai/archiprojects.md`, `ai/cross-project-signals.md`; skills `hub-project-create/`, `hub-project-register/`, `hub-project-migrate/`, `hub-project-switch/`, `hub-registry-check/`, `hub-local-router-install/` | — |
| tasks | skills `hub-task-intake/`, `hub-task-switch/`, `hub-task-finish/`, `hub-environment-check/`; `scripts/read-compact-task-index.py`, `scripts/task_records.py`, `scripts/check-all-task-records.sh`, `scripts/lib/calendar-date.sh` | — |
| knowledge | skills `hub-knowledge-enable/`, `hub-knowledge-capture/`, `hub-knowledge-review/`, `hub-info-update/` | — |
| calendar | skill `hub-calendar/` | `calendar-policy/`, `scripts/sync-calendar-policy.sh`, `scripts/grant-calendar-access.sh`, `scripts/build-calendar-bridge.sh` |
| planning | skill `hub-workflows/`; `hub-template/ai/workflow-context.md`; `scripts/snapshot-calendar.sh`, `scripts/calendar-context.py`, `scripts/calendar_task_sync.py`, `scripts/validate-day-plan-output.py` | — |
| goals | skill `hub-goal-progress/`; `hub-template/ai/goal-log.md`; `scripts/count-goal-progress.sh` | — |
| learning | skill `hub-session-review/`; `hub-template/ai/workflow-observations.md`; `scripts/workflow_friction.py`, `scripts/check-session-review.py`, `scripts/check-workflow-memory.sh` | — |
| obsidian | Task 1: `scripts/obsidian-task-sync.sh`, `scripts/generate-obsidian-projects-kanban.sh`. Task 3 moves them to `modules/obsidian/scripts/` and adds `modules/obsidian/rules.md -> ai/rules/obsidian.md` | Task 3: `modules/obsidian/scripts/obsidian-task-sync-watch.sh`, `modules/obsidian/scripts/install-obsidian-task-sync.sh`, `modules/obsidian/tests/` |
| release | — | `scripts/hub_release.py`, `scripts/module_passports.py`, `scripts/check-module-boundaries.py`, `scripts/update-installed-hub.sh`, `scripts/install-hub.sh`, `scripts/install.sh`, `scripts/check-consistency.sh`, `scripts/architecture-test.sh`, `scripts/hub-smoke-test.sh`, `tests/` |

Skill paths are `hub-template/ai/skills/<name>/ -> ai/skills/<name>/`. `hub-template/X -> X` for every other template file.

Dependencies and flags (copy from the spec table): core `Required: yes`, `Depends: —`; projects `yes`, `core`; tasks `yes`, `core, projects`; knowledge `no`, `core, projects`; calendar `no`, `core`; planning `no`, `core, projects, tasks, calendar`, `Uses if present: goals, learning`; goals `no`, `core, projects`; obsidian `no`, `core, projects, tasks`, `Switchable: yes`, `Keywords: Obsidian, obsidian-vault`; learning `no`, `core`; release `no`, `—`. All others `Switchable: no`, `Keywords: —`.

---

### Task 1: Passport parser, ten passports, ownership test

**Files:**
- Create: `scripts/module_passports.py`
- Create: `modules/{core,projects,tasks,knowledge,calendar,planning,goals,obsidian,learning,release}/module.md`
- Test: `tests/test_module_passports.py`

**Interfaces:**
- Produces (used by Tasks 2, 5, 6):
  - `Passport` dataclass: `id: str`, `required: bool`, `switchable: bool`, `depends: list[str]`, `uses_if_present: list[str]`, `rules: str | None` (Hub path), `keywords: list[str]`, `installs: list[tuple[str, str]]` (raw lines, directories end with `/`), `repo_only: list[str]`, `subscribes: dict[str, str]` (event → command), `purpose: str`.
  - `EVENTS = ("after-task-write", "before-task-confirmation")`
  - `parse_passport(path: Path) -> Passport` (raises `ValueError` on missing `Id:` or malformed line)
  - `load_passports(root: Path) -> dict[str, Passport]` (reads `root/modules/*/module.md`; `Id:` must equal folder name)
  - `install_pairs(root: Path, passports: dict, selected: list[str]) -> list[tuple[str, str]]` (expands `/` entries to every file below, recursively, sorted; skips `__pycache__`, `*.pyc`; raises `ValueError` on a missing source)
  - `installable(passports) -> list[str]` (sorted IDs whose `installs` is non-empty)
  - `resolve_selection(passports, previous: list[str] | None, with_: list[str], without: list[str]) -> list[str]`
  - `render_modules_md(passports, selected: list[str]) -> str`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_module_passports.py
import tempfile
import unittest
from pathlib import Path

from scripts.module_passports import (
    install_pairs, installable, load_passports, parse_passport,
    render_modules_md, resolve_selection,
)

ROOT = Path(__file__).resolve().parents[1]
SPEC_MODULES = {"core", "projects", "tasks", "knowledge", "calendar", "planning",
                "goals", "obsidian", "learning", "release"}


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


PASSPORT = """# Module: demo

Id: demo
Required: no
Switchable: yes
Depends: core, tasks
Uses if present: —
Rules: ai/rules/demo.md
Keywords: Demo, demo-vault

## Purpose

Demo module.

## Installs

- modules/demo/scripts/ -> scripts/
- modules/demo/rules.md -> ai/rules/demo.md

## Repository only

- modules/demo/tests/

## Reads

- project task files

## Writes

- —

## Subscribes

- after-task-write: bash scripts/demo.sh --hub <hub>
"""


class ParseTests(unittest.TestCase):
    def test_parse_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "modules/demo/module.md"
            write(path, PASSPORT)
            p = parse_passport(path)
            self.assertEqual(p.id, "demo")
            self.assertFalse(p.required)
            self.assertTrue(p.switchable)
            self.assertEqual(p.depends, ["core", "tasks"])
            self.assertEqual(p.uses_if_present, [])
            self.assertEqual(p.rules, "ai/rules/demo.md")
            self.assertEqual(p.keywords, ["Demo", "demo-vault"])
            self.assertEqual(p.installs, [("modules/demo/scripts/", "scripts/"),
                                          ("modules/demo/rules.md", "ai/rules/demo.md")])
            self.assertEqual(p.repo_only, ["modules/demo/tests/"])
            self.assertEqual(p.subscribes, {"after-task-write": "bash scripts/demo.sh --hub <hub>"})

    def test_missing_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "modules/demo/module.md"
            write(path, PASSPORT.replace("Id: demo\n", ""))
            with self.assertRaises(ValueError):
                parse_passport(path)

    def test_unknown_event_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "modules/demo/module.md"
            write(path, PASSPORT.replace("after-task-write:", "on-anything:"))
            with self.assertRaises(ValueError):
                parse_passport(path)

    def test_directory_install_expands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "modules/demo/module.md", PASSPORT)
            write(root / "modules/demo/scripts/demo.sh", "echo\n")
            write(root / "modules/demo/scripts/lib/x.sh", "echo\n")
            write(root / "modules/demo/rules.md", "# rules\n")
            passports = load_passports(root)
            self.assertEqual(install_pairs(root, passports, ["demo"]), [
                ("modules/demo/rules.md", "ai/rules/demo.md"),
                ("modules/demo/scripts/demo.sh", "scripts/demo.sh"),
                ("modules/demo/scripts/lib/x.sh", "scripts/lib/x.sh"),
            ])


def fake(passports_text):
    """Build passports from {id: (required, switchable, depends)}."""
    from scripts.module_passports import Passport
    return {i: Passport(id=i, required=r, switchable=s, depends=d, uses_if_present=[],
                        rules=None, keywords=[], installs=[("x", "y")], repo_only=[],
                        subscribes={}, purpose="")
            for i, (r, s, d) in passports_text.items()}


class SelectionTests(unittest.TestCase):
    P = fake({"core": (True, False, []), "tasks": (True, False, ["core"]),
              "obsidian": (False, True, ["core", "tasks"]),
              "planning": (False, False, ["core", "tasks"])})

    def test_no_previous_selects_all(self):
        self.assertEqual(resolve_selection(self.P, None, [], []),
                         ["core", "obsidian", "planning", "tasks"])

    def test_previous_selection_is_kept(self):
        self.assertEqual(resolve_selection(self.P, ["core", "tasks", "planning"], [], []),
                         ["core", "planning", "tasks"])

    def test_without_and_with(self):
        self.assertEqual(resolve_selection(self.P, None, [], ["obsidian"]),
                         ["core", "planning", "tasks"])
        self.assertEqual(resolve_selection(self.P, ["core", "tasks"], ["obsidian"], []),
                         ["core", "obsidian", "tasks"])

    def test_refusals(self):
        for with_, without in (([], ["core"]), ([], ["planning"]), (["nope"], []), ([], ["nope"])):
            with self.assertRaises(ValueError):
                resolve_selection(self.P, None, with_, without)

    def test_missing_dependency_is_refused(self):
        p = fake({"core": (True, False, []), "a": (False, True, ["b"]), "b": (False, True, [])})
        with self.assertRaises(ValueError):
            resolve_selection(p, None, [], ["b"])

    def test_required_modules_always_present(self):
        self.assertIn("tasks", resolve_selection(self.P, ["core"], [], []))


class RenderTests(unittest.TestCase):
    def test_modules_md_lists_subscribers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "modules/demo/module.md", PASSPORT)
            write(root / "modules/core/module.md", PASSPORT.replace("demo", "core")
                  .replace("Depends: core, tasks", "Depends: —").replace("- after-task-write: bash scripts/core.sh --hub <hub>\n", "- —\n"))
            passports = load_passports(root)
            text = render_modules_md(passports, ["core", "demo"])
            self.assertIn("- demo — rules: `ai/rules/demo.md`", text)
            self.assertIn("### after-task-write\n\n- demo: `bash scripts/demo.sh --hub <hub>` — rules: `ai/rules/demo.md`", text)
            self.assertIn("### before-task-confirmation\n\n- —", text)
            text = render_modules_md(passports, ["core"])
            self.assertIn("### after-task-write\n\n- —", text)


class RepositoryPassportTests(unittest.TestCase):
    def test_every_spec_module_has_a_passport(self):
        self.assertEqual(set(load_passports(ROOT)), SPEC_MODULES)

    def test_every_template_file_has_exactly_one_owner(self):
        passports = load_passports(ROOT)
        owners = {}
        for module_id in passports:
            for source, _ in install_pairs(ROOT, passports, [module_id]):
                owners.setdefault(source, []).append(module_id)
        template = {str(p.relative_to(ROOT)) for p in (ROOT / "hub-template").rglob("*") if p.is_file()}
        self.assertEqual(sorted(template - set(owners)), [])
        self.assertEqual({s: o for s, o in owners.items() if len(o) > 1}, {})

    def test_dependencies_reference_known_modules(self):
        passports = load_passports(ROOT)
        for p in passports.values():
            for dep in p.depends + p.uses_if_present:
                self.assertIn(dep, passports, f"{p.id} -> {dep}")

    def test_only_obsidian_is_switchable(self):
        passports = load_passports(ROOT)
        self.assertEqual([p.id for p in passports.values() if p.switchable], ["obsidian"])

    def test_release_installs_nothing(self):
        self.assertNotIn("release", installable(load_passports(ROOT)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `python3 -m unittest tests.test_module_passports -v`
Expected: FAIL/ERROR `ModuleNotFoundError: No module named 'scripts.module_passports'`.

- [ ] **Step 3: Implement `scripts/module_passports.py`**

```python
#!/usr/bin/env python3
"""Read module passports (modules/<id>/module.md) with the standard library only."""

import re
from dataclasses import dataclass, field
from pathlib import Path

EVENTS = ("after-task-write", "before-task-confirmation")
HEADERS = {"Id", "Required", "Switchable", "Depends", "Uses if present", "Rules", "Keywords"}
SECTIONS = {"Purpose", "Installs", "Repository only", "Reads", "Writes", "Subscribes"}
EMPTY = "—"


@dataclass
class Passport:
    id: str
    required: bool
    switchable: bool
    depends: list = field(default_factory=list)
    uses_if_present: list = field(default_factory=list)
    rules: object = None
    keywords: list = field(default_factory=list)
    installs: list = field(default_factory=list)
    repo_only: list = field(default_factory=list)
    subscribes: dict = field(default_factory=dict)
    purpose: str = ""


def _items(value):
    value = value.strip()
    return [] if value in ("", EMPTY) else [part.strip() for part in value.split(",")]


def _flag(value, name, path):
    if value not in ("yes", "no"):
        raise ValueError(f"{path}: {name} must be yes or no")
    return value == "yes"


def parse_passport(path):
    path = Path(path)
    headers, sections, current = {}, {name: [] for name in SECTIONS}, None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current = line[3:].strip()
            if current not in SECTIONS:
                raise ValueError(f"{path}: unknown section {current}")
            continue
        if current is None:
            match = re.match(r"^([A-Za-z ]+):\s*(.*)$", line)
            if match and match.group(1) in HEADERS:
                headers[match.group(1)] = match.group(2).strip()
            continue
        sections[current].append(line)
    if "Id" not in headers:
        raise ValueError(f"{path}: missing Id")

    def bullets(name):
        out = []
        for line in sections[name]:
            if line.startswith("- "):
                item = line[2:].strip()
                if item != EMPTY:
                    out.append(item)
        return out

    installs = []
    for item in bullets("Installs"):
        if " -> " not in item:
            raise ValueError(f"{path}: install line needs 'source -> target': {item}")
        source, target = (part.strip().strip("`") for part in item.split(" -> ", 1))
        installs.append((source, target))
    subscribes = {}
    for item in bullets("Subscribes"):
        event, _, command = item.partition(":")
        if event.strip() not in EVENTS or not command.strip():
            raise ValueError(f"{path}: bad subscription {item}")
        subscribes[event.strip()] = command.strip().strip("`")
    rules = headers.get("Rules", EMPTY)
    return Passport(
        id=headers["Id"],
        required=_flag(headers.get("Required", "no"), "Required", path),
        switchable=_flag(headers.get("Switchable", "no"), "Switchable", path),
        depends=_items(headers.get("Depends", EMPTY)),
        uses_if_present=_items(headers.get("Uses if present", EMPTY)),
        rules=None if rules == EMPTY else rules.strip("`"),
        keywords=_items(headers.get("Keywords", EMPTY)),
        installs=installs,
        repo_only=[item.strip("`") for item in bullets("Repository only")],
        subscribes=subscribes,
        purpose="\n".join(sections["Purpose"]).strip(),
    )


def load_passports(root):
    passports = {}
    for path in sorted(Path(root).glob("modules/*/module.md")):
        passport = parse_passport(path)
        if passport.id != path.parent.name:
            raise ValueError(f"{path}: Id {passport.id} differs from folder")
        passports[passport.id] = passport
    return passports


def install_pairs(root, passports, selected):
    root = Path(root)
    pairs = []
    for module_id in selected:
        for source, target in passports[module_id].installs:
            if source.endswith("/"):
                base = root / source
                if not base.is_dir():
                    raise ValueError(f"missing install directory: {source}")
                for path in sorted(base.rglob("*")):
                    if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
                        continue
                    rel = path.relative_to(base).as_posix()
                    pairs.append((source + rel, target + rel))
            else:
                if not (root / source).is_file():
                    raise ValueError(f"missing install file: {source}")
                pairs.append((source, target))
    return sorted(pairs)


def installable(passports):
    return sorted(i for i, p in passports.items() if p.installs)


def resolve_selection(passports, previous, with_, without):
    for module_id in list(with_) + list(without):
        if module_id not in passports:
            raise ValueError(f"unknown module: {module_id}")
        if not passports[module_id].switchable:
            raise ValueError(f"module cannot be switched: {module_id}")
    available = set(installable(passports))
    chosen = available if previous is None else set(previous) & available
    chosen |= {i for i, p in passports.items() if p.required}
    chosen = (chosen | set(with_)) - set(without)
    for module_id in sorted(chosen):
        for dep in passports[module_id].depends:
            if dep not in chosen:
                raise ValueError(f"module {module_id} requires {dep}")
    return sorted(chosen)


def render_modules_md(passports, selected):
    lines = ["# Installed Modules", "",
             "Generated by the Hub installer from module passports. Do not edit.", "",
             "## Modules", ""]
    for module_id in selected:
        rules = passports[module_id].rules
        lines.append(f"- {module_id}" + (f" — rules: `{rules}`" if rules else ""))
    lines += ["", "## Events", ""]
    for event in EVENTS:
        lines += [f"### {event}", ""]
        subscribers = [i for i in selected if event in passports[i].subscribes]
        for module_id in subscribers:
            p = passports[module_id]
            suffix = f" — rules: `{p.rules}`" if p.rules else ""
            lines.append(f"- {module_id}: `{p.subscribes[event]}`{suffix}")
        if not subscribers:
            lines.append(f"- {EMPTY}")
        lines.append("")
    return "\n".join(lines)
```

- [ ] **Step 4: Write the ten passports** using the ownership table above. Template (obsidian, current paths for now):

```markdown
# Module: obsidian

Id: obsidian
Required: no
Switchable: yes
Depends: core, projects, tasks
Uses if present: —
Rules: —
Keywords: Obsidian, obsidian-vault

## Purpose

Read-only projection of projects and tasks into the central Obsidian vault;
manual board edits become proposals back, never direct task writes.

## Installs

- scripts/obsidian-task-sync.sh -> scripts/obsidian-task-sync.sh
- scripts/generate-obsidian-projects-kanban.sh -> scripts/generate-obsidian-projects-kanban.sh

## Repository only

- scripts/obsidian-task-sync-watch.sh
- scripts/install-obsidian-task-sync.sh

## Reads

- registry and project cards (projects)
- project task files (tasks)

## Writes

- the central vault `projects/ai-dev-architecture/obsidian-vault`
- task files only through a confirmed reverse proposal applied by the user

## Subscribes

- —
```

For `core` write `Rules: ai/architecture.md`; every other module `Rules: —` in this task. `release` has `## Installs` with `- —`. Each `## Reads`/`## Writes` is 1–3 plain lines taken from the spec's data-owner table.

- [ ] **Step 5: Run tests** — `python3 -m unittest tests.test_module_passports -v` → PASS. Also break one passport on purpose (delete one skill line from `projects`), confirm `test_every_template_file_has_exactly_one_owner` fails, restore.

- [ ] **Step 6: Commit**

```bash
git add scripts/module_passports.py modules tests/test_module_passports.py
git commit -m "feat: паспорта модулей и их чтение"
```

---

### Task 2: Manifest from passports, module selection, `ai/modules.md`

**Files:**
- Modify: `scripts/hub_release.py` (remove `RUNTIME_SCRIPTS`; change `build_manifest`, `preview`, `apply`, `drift`, `main`)
- Modify: `tests/test_hub_release.py`, `tests/test_hub_release_retired.py` (replace `RUNTIME_SCRIPTS` copying)
- Test: `tests/test_module_selection.py`

**Interfaces:**
- Consumes: `load_passports`, `install_pairs`, `installable`, `resolve_selection`, `render_modules_md` from Task 1.
- Produces:
  - `build_manifest(source, modules=None) -> dict` with keys `format`, `modules` (sorted list), `files`, `remove`, `ignore_lines`. The file entry for `ai/modules.md` is `{"source": None, "target": "ai/modules.md", "sha256": ..., "mode": 420, "policy": "managed", "content": <text>}`.
  - `preview(source, hub, source_sha=None, with_=(), without=())`; payload gains `modules` and `previous_modules` (list or `None`).
  - `apply(source, hub, confirmed_plan, source_sha=None, confirmed_source_sha=None, with_=(), without=())`.
  - `release_sources(root) -> list[str]` in `hub_release.py`: every source file of every installable module plus every `modules/*/module.md` (for tests copying a source tree).
  - CLI: `preview` and `apply` accept repeatable `--with ID` / `--without ID`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_module_selection.py
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.hub_release import apply, build_manifest, drift, preview, release_sources

ROOT = Path(__file__).resolve().parents[1]
OBSIDIAN_TARGETS = {"scripts/obsidian-task-sync.sh", "scripts/generate-obsidian-projects-kanban.sh"}


def install(hub, **kw):
    plan = preview(ROOT, hub, **kw)
    apply(ROOT, hub, plan["plan_sha256"], **kw)
    return plan


class ModuleSelectionTests(unittest.TestCase):
    def test_full_manifest_has_all_modules_and_modules_md(self):
        manifest = build_manifest(ROOT)
        self.assertIn("obsidian", manifest["modules"])
        targets = {e["target"] for e in manifest["files"]}
        self.assertTrue(OBSIDIAN_TARGETS <= targets)
        entry = next(e for e in manifest["files"] if e["target"] == "ai/modules.md")
        self.assertIn("## Events", entry["content"])

    def test_manifest_without_obsidian(self):
        manifest = build_manifest(ROOT, ["calendar", "core", "goals", "knowledge",
                                         "learning", "planning", "projects", "tasks"])
        targets = {e["target"] for e in manifest["files"]}
        self.assertFalse(OBSIDIAN_TARGETS & targets)

    def test_selection_persists_and_modules_md_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp) / "hub"
            hub.mkdir()
            install(hub, without=["obsidian"])
            installed = json.loads((hub / ".local/hub-release/installed.json").read_text())
            self.assertNotIn("obsidian", installed["modules"])
            self.assertIn("- core", (hub / "ai/modules.md").read_text())
            again = preview(ROOT, hub)
            self.assertEqual(again["modules"], installed["modules"])
            self.assertEqual({r["action"] for r in again["operations"]}, {"keep"})
            self.assertEqual(drift(ROOT, hub), {"conflicts": [], "unmanaged": []})

    def test_metadata_without_modules_key_means_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp) / "hub"
            hub.mkdir()
            install(hub)
            meta = hub / ".local/hub-release/installed.json"
            data = json.loads(meta.read_text())
            data.pop("modules")
            meta.write_text(json.dumps(data))
            self.assertIsNone(preview(ROOT, hub)["previous_modules"])
            self.assertIn("obsidian", preview(ROOT, hub)["modules"])

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp) / "hub"
            hub.mkdir()
            for kw in ({"without": ["tasks"]}, {"without": ["planning"]}, {"with_": ["nope"]}):
                with self.assertRaises(ValueError):
                    preview(ROOT, hub, **kw)

    def test_release_sources_cover_manifest(self):
        sources = set(release_sources(ROOT))
        for entry in build_manifest(ROOT)["files"]:
            if entry["source"] is not None:
                self.assertIn(entry["source"], sources)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python3 -m unittest tests.test_module_selection -v` → ImportError on `release_sources`.

- [ ] **Step 3: Implement in `scripts/hub_release.py`**

Top of file, after stdlib imports:

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from module_passports import install_pairs, installable, load_passports, render_modules_md, resolve_selection  # noqa: E402
```

Delete `RUNTIME_SCRIPTS`. Replace `build_manifest`:

```python
MODULES_FILE = "ai/modules.md"


def is_memory_target(target):
    return target in MEMORY_FILES or target.startswith(("ai/project-cards/", "ai/archive/"))


def build_manifest(source, modules=None):
    root = source_root(source)
    passports = load_passports(root)
    selected = sorted(modules) if modules is not None else installable(passports)
    files = [file_entry(root, src, target, "create-if-missing" if is_memory_target(target) else "managed")
             for src, target in install_pairs(root, passports, selected)]
    text = render_modules_md(passports, selected)
    files.append({"source": None, "target": MODULES_FILE,
                  "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                  "mode": 0o644, "policy": "managed", "content": text})
    files.sort(key=lambda entry: entry["target"])
    if len({entry["target"] for entry in files}) != len(files):
        raise ValueError("duplicate manifest target")
    return {"format": 1, "modules": selected, "files": files, "remove": [],
            "ignore_lines": ["/.local/", "/projects/"]}


def release_sources(root):
    root = source_root(root)
    passports = load_passports(root)
    sources = {src for src, _ in install_pairs(root, passports, installable(passports))}
    sources |= {str(p.relative_to(root)) for p in root.glob("modules/*/module.md")}
    return sorted(sources)
```

In `preview`, load installed metadata first and resolve the selection:

```python
def preview(source, hub, source_sha=None, with_=(), without=()):
    source_sha = normalize_source_sha(source_sha)
    hub = hub.resolve()
    installed_file = hub / ".local" / "hub-release" / "installed.json"
    installed_manifest = load_installed_manifest(installed_file)
    previous_modules = installed_manifest.get("modules")
    selected = resolve_selection(load_passports(source_root(source)), previous_modules, list(with_), list(without))
    manifest = build_manifest(source, selected)
    # ... existing operations loop unchanged ...
    payload = {"manifest": manifest, "operations": operations, "source_sha": source_sha,
               "modules": selected, "previous_modules": previous_modules}
```

In `apply`, add `with_=(), without=()` parameters, pass them to `preview`, and stage generated content:

```python
        for row in staged_changes:
            entry = entries[row["target"]]
            staged = staging / row["target"]
            staged.parent.mkdir(parents=True, exist_ok=True)
            if entry.get("content") is not None:
                staged.write_text(entry["content"], encoding="utf-8")
            else:
                shutil.copyfile(source_root(source) / entry["source"], staged)
            os.chmod(staged, entry["mode"])
```

In `main`, for `preview` and `apply` parsers add:

```python
        command.add_argument("--with", dest="with_", action="append", default=[])
        command.add_argument("--without", action="append", default=[])
```

and pass `with_=args.with_, without=args.without`.

In both existing test files replace the `RUNTIME_SCRIPTS` import and copy loop with:

```python
from scripts.hub_release import apply, preview, release_sources  # plus the names each file already imports
...
        for relative in release_sources(ROOT):
            src, dst = ROOT / relative, source / relative
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
```

Remove the separate `shutil.copytree(ROOT / "hub-template", ...)` line, since `release_sources` already includes every template file. `test_release_includes_*` tests keep asserting targets through `build_manifest(ROOT)`.

- [ ] **Step 4: Run** `python3 -m unittest discover -s tests -p 'test_*.py'` → all PASS. `python3 scripts/hub_release.py drift --source . --hub /Users/zykovsrg/Documents/vibecode/_ai-hub` now reports `ai/modules.md` missing; that is expected (it is created at the Task 7 update). Do not change the Hub here.

- [ ] **Step 5: Commit** — `git commit -m "feat: список файлов установки строится из паспортов, выбор модулей запоминается"`

---

### Task 3: Move Obsidian into `modules/obsidian`, rules file, architecture pointer

**Files:**
- Move (`git mv`): `scripts/obsidian-task-sync.sh`, `scripts/generate-obsidian-projects-kanban.sh`, `scripts/obsidian-task-sync-watch.sh`, `scripts/install-obsidian-task-sync.sh` → `modules/obsidian/scripts/`; `scripts/obsidian-projects-kanban-test.sh`, `scripts/obsidian-task-sync-test.sh`, `scripts/obsidian-task-sync-watch-test.sh`, `tests/test_scoped_obsidian_refresh.py` → `modules/obsidian/tests/`
- Create: `modules/obsidian/rules.md`, `modules/obsidian/tests/stage-scripts.sh`
- Modify: `modules/obsidian/module.md`, `hub-template/ai/architecture.md`, `scripts/architecture-test.sh`, `.github/workflows/hub-architecture-tests.yml`

**Interfaces:**
- Consumes: Task 2 manifest (targets stay `scripts/obsidian-task-sync.sh`, `scripts/generate-obsidian-projects-kanban.sh`) and adds `ai/rules/obsidian.md`.
- Produces: `modules/obsidian/rules.md` whose refresh command equals the passport `after-task-write` command; `stage-scripts.sh <dir>` copies the Hub-layout script set into `<dir>`.

- [ ] **Step 1: Search decisions.** Run `grep -n "obsidian-task-sync\|generate-obsidian\|install-obsidian\|obsidian-vault" ai/decisions.md`. Files are moved, not deleted; report hits in the task summary.

- [ ] **Step 2: Move files** with `git mv` (list above).

- [ ] **Step 3: Staging helper.** The scripts expect `task_records.py` and `lib/calendar-date.sh` next to them (Hub layout). Create `modules/obsidian/tests/stage-scripts.sh`:

```bash
#!/usr/bin/env bash
# Copy the Obsidian scripts and the task helpers they call into one directory (Hub layout).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
DEST="${1:?usage: stage-scripts.sh <dir>}"
mkdir -p "$DEST/lib"
cp -p "$ROOT"/modules/obsidian/scripts/*.sh "$DEST/"
cp -p "$ROOT/scripts/task_records.py" "$DEST/"
cp -p "$ROOT/scripts/lib/calendar-date.sh" "$DEST/lib/"
```

In each moved shell test: set `ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"`. After its temp dir is created, add `STAGE="$TMP_DIR/stage"; bash "$ROOT/modules/obsidian/tests/stage-scripts.sh" "$STAGE"`, using the test's own temp variable name. Replace `$ROOT/scripts/<obsidian script>` with `$STAGE/<obsidian script>`. Leave other `$ROOT/...` paths unchanged. In `test_scoped_obsidian_refresh.py`: set `ROOT = Path(__file__).resolve().parents[3]`. When `OBSIDIAN_GENERATOR` is unset, run `stage-scripts.sh` once in `setUpModule` into a `tempfile.mkdtemp(dir="/private/tmp")` directory and use it as the default generator. Remove that directory in `tearDownModule`.

- [ ] **Step 4: Run the moved tests from the new place** and expect PASS:
`bash modules/obsidian/tests/obsidian-projects-kanban-test.sh && bash modules/obsidian/tests/obsidian-task-sync-test.sh && bash modules/obsidian/tests/obsidian-task-sync-watch-test.sh && python3 -m unittest discover -s modules/obsidian/tests -p 'test_*.py' -v`

- [ ] **Step 5: Rules file.** Create `modules/obsidian/rules.md` from three sources:
  1. the `## Central Obsidian Projection` section of `hub-template/ai/architecture.md` (vault path, board path, scan/apply commands, "never written automatically");
  2. the vault/scope paragraphs from `hub-task-intake/SKILL.md` §Procedure (scope file with the confirmed ID only, partial vs full refresh, blocked refresh);
  3. the step-5/6 refresh and reverse-proposal text.

  Structure: `# Obsidian Module Rules`, `## Vault`, `## after-task-write` (the command `bash scripts/generate-obsidian-projects-kanban.sh --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault --write --refresh-from-architecture`, manifest validation on; on a manual-edit block run `scan --project-id` and report the pending proposal), `## Reverse proposals` (scan/apply commands; apply only after the user confirms the proposal SHA). Remove the section from `architecture.md` and add in its place:

```markdown
## Module Rules

Optional modules install their rules as `ai/rules/<id>.md`. The installer
lists installed modules and event subscribers in the generated
`ai/modules.md`. A module's rules are read only when one of its commands or
subscriptions runs; a module that is not installed is never called.
```

  Bump `Version: 1.12` → `Version: 1.13`.

- [ ] **Step 6: Update the obsidian passport**:

```markdown
Rules: ai/rules/obsidian.md

## Installs

- modules/obsidian/scripts/obsidian-task-sync.sh -> scripts/obsidian-task-sync.sh
- modules/obsidian/scripts/generate-obsidian-projects-kanban.sh -> scripts/generate-obsidian-projects-kanban.sh
- modules/obsidian/rules.md -> ai/rules/obsidian.md

## Repository only

- modules/obsidian/scripts/obsidian-task-sync-watch.sh
- modules/obsidian/scripts/install-obsidian-task-sync.sh
- modules/obsidian/tests/

## Subscribes

- after-task-write: bash scripts/generate-obsidian-projects-kanban.sh --hub <hub> --scope <scope-file> --vault <hub>/projects/ai-dev-architecture/obsidian-vault --write --refresh-from-architecture
```

- [ ] **Step 7: Runners.** In `scripts/architecture-test.sh`, `integration()` calls `bash "$ROOT/modules/obsidian/tests/obsidian-projects-kanban-test.sh"` and `bash "$ROOT/modules/obsidian/tests/obsidian-task-sync-test.sh"`. `unit()` adds `python3 -m unittest discover -s "$ROOT/modules/obsidian/tests" -p 'test_*.py' -v` and `bash "$ROOT/modules/obsidian/tests/obsidian-task-sync-watch-test.sh"`. In the CI workflow, after the `python3 -m unittest discover -s tests -v` step, add a step `python3 -m unittest discover -s modules/obsidian/tests -v`.

- [ ] **Step 8: Add a test** to `tests/test_module_selection.py`:

```python
    def test_obsidian_rules_command_matches_subscription(self):
        from scripts.module_passports import load_passports
        command = load_passports(ROOT)["obsidian"].subscribes["after-task-write"]
        self.assertIn(command, (ROOT / "modules/obsidian/rules.md").read_text(encoding="utf-8"))
```

- [ ] **Step 9: Run** `bash scripts/architecture-test.sh --unit` (or the unit + integration functions as the script supports) and `bash scripts/check-consistency.sh`. Everything passes except the known local-only failures listed in `ai/changelog.md` 2026-09-27 (`check-consistency.sh` local `ai/skills/`, `hub-smoke-test.sh` `/tmp` symlink). Compare against `git stash`-free baseline output if unsure.

- [ ] **Step 10: Commit** — `git commit -m "refactor: Obsidian переехал в modules/obsidian, правила — отдельным файлом"`

---

### Task 4: `after-task-write` event in skills; strict "no Obsidian outside its module"

**Files:**
- Modify: `hub-template/ai/skills/hub-task-intake/SKILL.md`, `hub-task-switch/SKILL.md`, `hub-task-finish/SKILL.md`, `hub-info-update/SKILL.md`, `hub-calendar/resources/joint-task-change.md`
- Test: `tests/test_module_events.py`

**Interfaces:**
- Consumes: `load_passports`, `install_pairs` (Task 1); Hub path `ai/modules.md` (Task 2).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_module_events.py
import re
import unittest
from pathlib import Path

from scripts.module_passports import install_pairs, load_passports

ROOT = Path(__file__).resolve().parents[1]
NO_OBSIDIAN = ["core", "projects", "tasks", "knowledge", "calendar"]
EVENT_SKILLS = ["hub-task-intake", "hub-task-switch", "hub-task-finish", "hub-info-update"]


class ObsidianIsolationTests(unittest.TestCase):
    def test_no_obsidian_outside_its_module(self):
        passports = load_passports(ROOT)
        hits = []
        for module_id in NO_OBSIDIAN:
            for source, _ in install_pairs(ROOT, passports, [module_id]):
                text = (ROOT / source).read_text(encoding="utf-8", errors="replace")
                if re.search(r"obsidian", text, re.I):
                    hits.append(source)
        self.assertEqual(hits, [])

    def test_task_skills_fire_after_task_write(self):
        for skill in EVENT_SKILLS:
            text = (ROOT / f"hub-template/ai/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("`after-task-write`", text, skill)
            self.assertIn("ai/modules.md", text, skill)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** `python3 -m unittest tests.test_module_events -v`. Expect FAIL, with hits listing the four skills and `joint-task-change.md`. This is the "seen failing" evidence.

- [ ] **Step 3: Edit skills.** In each of the four skills, delete every Obsidian paragraph and command block: the vault/board/reverse-command block, the scope-file paragraph, the refresh step, and the Obsidian-to-`ai/` step. Put this paragraph where the refresh step was, keeping the step number and renumbering the ones that follow:

```markdown
N. After a confirmed write to the selected project's task files, run the
   `after-task-write` event: read `<hub>/ai/modules.md`; for each subscriber
   listed under `after-task-write`, read its rules file and run its command
   for the confirmed project ID only. With no subscribers, do nothing. If a
   subscriber reports a pending proposal, show it and never apply it without
   its own explicit confirmation.
```

In `hub-info-update`, use the same text in the "After every approved selected-project write" sentence. In `joint-task-change.md`, replace "For a dated task change from Obsidian" with "For a dated task change that arrives as a pending proposal from an `after-task-write` subscriber". Replace "refresh generated boards" with "run the `after-task-write` event (see `ai/modules.md`)".

- [ ] **Step 4: Run** `python3 -m unittest tests.test_module_events -v` → PASS; `bash scripts/check-consistency.sh` shows no new failures versus Task 3. Full unit suite passes.

- [ ] **Step 5: Commit** — `git commit -m "feat: навыки задач вызывают модули через событие after-task-write"`

---

### Task 5: Boundary check (warning mode)

**Files:**
- Create: `scripts/check-module-boundaries.py`
- Test: `tests/test_module_boundaries.py`
- Modify: `scripts/architecture-test.sh` (`unit()` runs the check in warning mode), `modules/release/module.md` (already lists it under Repository only; add if missing)

**Interfaces:**
- Consumes: `load_passports`, `install_pairs`.
- Produces: `find_violations(root: Path) -> list[tuple[str, str, str]]` (`file`, `module`, `token`), sorted; CLI `python3 scripts/check-module-boundaries.py --source <root> [--strict]`.

- [ ] **Step 1: Write failing tests** (fixture repository, so the check is seen failing):

```python
# tests/test_module_boundaries.py
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check-module-boundaries.py"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def passport(module_id, depends, installs, keywords="—"):
    lines = "\n".join(f"- {s} -> {t}" for s, t in installs)
    return (f"# Module: {module_id}\n\nId: {module_id}\nRequired: no\nSwitchable: no\n"
            f"Depends: {depends}\nUses if present: —\nRules: —\nKeywords: {keywords}\n\n"
            f"## Purpose\n\nx\n\n## Installs\n\n{lines}\n")


class BoundaryTests(unittest.TestCase):
    def fixture(self, root, a_depends):
        write(root / "modules/core/module.md", passport("core", "—", [("core/rules.md", "ai/rules.md")]))
        write(root / "core/rules.md", "core\n")
        write(root / "modules/a/module.md", passport("a", a_depends, [("a/skills/hub-a/SKILL.md", "ai/skills/hub-a/SKILL.md")]))
        write(root / "a/skills/hub-a/SKILL.md", "Run `bash scripts/b-tool.sh` and see the Vault note.\n")
        write(root / "modules/b/module.md", passport("b", "core", [("b/b-tool.sh", "scripts/b-tool.sh")], "Vault"))
        write(root / "b/b-tool.sh", "echo b\n")

    def run_check(self, root, *flags):
        return subprocess.run([sys.executable, str(SCRIPT), "--source", str(root), *flags],
                              capture_output=True, text=True, check=False)

    def test_violation_is_reported_but_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, "core")
            result = self.run_check(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("WARN a/skills/hub-a/SKILL.md: b via b-tool.sh", result.stdout)
            self.assertIn("WARN a/skills/hub-a/SKILL.md: b via Vault", result.stdout)

    def test_strict_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, "core")
            self.assertEqual(self.run_check(root, "--strict").returncode, 1)

    def test_declared_dependency_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root, "core, b")
            result = self.run_check(root, "--strict")
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertNotIn("WARN", result.stdout)

    def test_repository_runs_in_warning_mode(self):
        result = self.run_check(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("via Obsidian", result.stdout)
        self.assertNotIn("via obsidian-", result.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run** → FAIL (script missing).

- [ ] **Step 3: Implement**

```python
#!/usr/bin/env python3
"""Warn when a module's installed files reference a module it may not depend on."""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from module_passports import install_pairs, load_passports  # noqa: E402

GENERIC = {"SKILL.md", ".gitkeep", "module.md", "README.md", "rules.md"}


def module_tokens(root, passports, module_id):
    tokens = {(k, True) for k in passports[module_id].keywords}
    for _, target in install_pairs(root, passports, [module_id]):
        parts = Path(target).parts
        if len(parts) >= 3 and parts[:2] == ("ai", "skills"):
            tokens.add((parts[2], False))
        elif parts[-1] not in GENERIC:
            tokens.add((parts[-1], False))
    return tokens


def find_violations(root):
    root = Path(root)
    passports = load_passports(root)
    tokens = {i: module_tokens(root, passports, i) for i in passports}
    violations = set()
    for module_id, passport in passports.items():
        allowed = {module_id, "core", *passport.depends, *passport.uses_if_present}
        for source, _ in install_pairs(root, passports, [module_id]):
            text = (root / source).read_text(encoding="utf-8", errors="replace")
            for other, other_tokens in tokens.items():
                if other in allowed:
                    continue
                for token, keyword in other_tokens:
                    pattern = r"(?<![A-Za-z0-9_.-])" + re.escape(token) + r"(?![A-Za-z0-9_-])"
                    if re.search(pattern, text, re.I if keyword else 0):
                        violations.add((source, other, token))
    return sorted(violations)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    violations = find_violations(args.source)
    for source, other, token in violations:
        print(f"WARN {source}: {other} via {token}")
    print(f"module boundaries: {len(violations)} warning(s)")
    return 1 if args.strict and violations else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run** the tests → PASS. Run `python3 scripts/check-module-boundaries.py` on the repository and paste the warning list into the task summary. Expected kinds: `hub-info-update` → tasks files; calendar → task words or planning scripts; core `architecture.md` → many modules. None may mention Obsidian.

- [ ] **Step 5:** Add `python3 "$ROOT/scripts/check-module-boundaries.py" --source "$ROOT"` to `unit()` in `scripts/architecture-test.sh`.

- [ ] **Step 6: Commit** — `git commit -m "feat: проверка границ модулей в режиме предупреждения"`

---

### Task 6: Updater flags, disable/re-enable end to end, docs

**Files:**
- Modify: `scripts/update-installed-hub.sh`, `docs/update.md`
- Test: `tests/test_obsidian_switch.py`

**Interfaces:**
- Consumes: `preview`/`apply` with `with_`/`without` (Task 2); CLI `--with/--without` on `hub_release.py`.
- Produces: `update-installed-hub.sh [--with ID]... [--without ID]...`; the preview prints `Modules: <list>` and, when it changes, `Module change: -obsidian` / `+obsidian`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_obsidian_switch.py
import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPDATER = ROOT / "scripts/update-installed-hub.sh"
REMOVED = {"scripts/obsidian-task-sync.sh", "scripts/generate-obsidian-projects-kanban.sh", "ai/rules/obsidian.md"}


def tree_digest(path):
    h = hashlib.sha256()
    for p in sorted(path.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(path)).encode()); h.update(p.read_bytes())
    return h.hexdigest()


class ObsidianSwitchTests(unittest.TestCase):
    def run_updater(self, hub, *args):
        return subprocess.run(["bash", str(UPDATER), "--source", str(ROOT), "--hub", str(hub), "--allow-dirty", *args],
                              capture_output=True, text=True, check=False)

    def plan_sha(self, output):
        return next(l.split(": ", 1)[1] for l in output.splitlines() if l.startswith("Plan SHA256: "))

    def installed_hub(self, root):
        hub = root / "_ai-hub"  # install-hub.sh requires this name and a symlink-free path
        subprocess.run(["bash", str(ROOT / "scripts/install-hub.sh"), str(hub)], check=True, capture_output=True)
        vault = hub / "projects/ai-dev-architecture/obsidian-vault/Obsidian"
        vault.mkdir(parents=True)
        (vault / "Board.md").write_text("board\n", encoding="utf-8")
        (hub / ".local/obsidian-scope").write_text("demo\n", encoding="utf-8")
        return hub

    def test_disable_then_enable(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            vault = hub / "projects/ai-dev-architecture/obsidian-vault"
            before = tree_digest(vault)

            dry = self.run_updater(hub, "--dry-run", "--without", "obsidian")
            self.assertEqual(dry.returncode, 0, dry.stderr)
            removed = {l.split(": ", 1)[1] for l in dry.stdout.splitlines() if l.startswith("remove: ")}
            self.assertEqual(removed, REMOVED)
            self.assertIn("replace: ai/modules.md", dry.stdout)
            self.assertIn("Module change: -obsidian", dry.stdout)

            applied = self.run_updater(hub, "--apply", "--without", "obsidian", "--confirm-plan", self.plan_sha(dry.stdout))
            self.assertEqual(applied.returncode, 0, applied.stderr)
            for target in REMOVED:
                self.assertFalse((hub / target).exists(), target)
            self.assertEqual(tree_digest(vault), before)
            self.assertEqual((hub / ".local/obsidian-scope").read_text(), "demo\n")
            self.assertNotIn("obsidian", (hub / "ai/modules.md").read_text().split("## Events")[0])

            check = self.run_updater(hub, "--check")
            self.assertEqual(check.returncode, 0, check.stdout)
            drift = subprocess.run(["python3", str(ROOT / "scripts/hub_release.py"), "drift",
                                    "--source", str(ROOT), "--hub", str(hub)], capture_output=True, text=True)
            self.assertEqual(drift.returncode, 0, drift.stdout)

            dry = self.run_updater(hub, "--dry-run", "--with", "obsidian")
            self.assertIn("Module change: +obsidian", dry.stdout)
            applied = self.run_updater(hub, "--apply", "--with", "obsidian", "--confirm-plan", self.plan_sha(dry.stdout))
            self.assertEqual(applied.returncode, 0, applied.stderr)
            for target in REMOVED:
                self.assertTrue((hub / target).exists(), target)

    def test_locally_changed_obsidian_script_blocks_disable(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            script = hub / "scripts/obsidian-task-sync.sh"
            script.write_text(script.read_text() + "\n# local\n")
            dry = self.run_updater(hub, "--dry-run", "--without", "obsidian")
            self.assertIn("conflict: scripts/obsidian-task-sync.sh", dry.stdout)
            applied = self.run_updater(hub, "--apply", "--without", "obsidian", "--confirm-plan", self.plan_sha(dry.stdout))
            self.assertNotEqual(applied.returncode, 0)
            self.assertTrue(script.exists())

    def test_required_module_cannot_be_disabled(self):
        with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
            hub = self.installed_hub(Path(tmp))
            result = self.run_updater(hub, "--dry-run", "--without", "tasks")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot be switched", result.stderr)


if __name__ == "__main__":
    unittest.main()
```

`install-hub.sh <dir>` requires the directory to be named `_ai-hub` and its path to contain no symlinks (macOS `/var` is a symlink), hence `/private/tmp`; CI already creates `/private/tmp`.

- [ ] **Step 2: Run** → FAIL (`unknown argument: --without` or similar).

- [ ] **Step 3: Implement in `update-installed-hub.sh`**

```bash
MODULE_ARGS=()
# in the argument case:
    --with|--without) opt="$1"; shift; [ "$#" -gt 0 ] || die "$opt requires a module id"; MODULE_ARGS+=("$opt" "$1") ;;
```

Pass `${MODULE_ARGS[@]+"${MODULE_ARGS[@]}"}` to both `hub_release.py preview` calls and both `apply` calls. Update `usage` with `[--with ID] [--without ID]`. Extend `print_plan`'s Python:

```python
print("Modules:", ", ".join(p["modules"]))
prev = p.get("previous_modules")
if prev is not None:
    change = [f"-{m}" for m in prev if m not in p["modules"]] + [f"+{m}" for m in p["modules"] if m not in prev]
    if change: print("Module change:", " ".join(change))
```

Then check the `hub_release.py` error path: `release error: module cannot be switched: tasks` must reach stderr, and the updater must exit non-zero. `set -e` with `PLAN_JSON="$(...)"` already does this; verify it.

- [ ] **Step 4: Docs.** In `docs/update.md` add a short Russian section «Модули»: how to switch off (`--without obsidian`) and back on (`--with obsidian`); the choice is remembered; the preview lists removed files; data and the vault are never deleted.

- [ ] **Step 5: Run** the new test and the full unit suite → PASS.

- [ ] **Step 6: Commit** — `git commit -m "feat: выключение и включение модуля при обновлении хаба"`

---

### Task 7: Working Hub, project memory, CI (controller only, needs user confirmations)

This task is done by the controller, not a subagent, because it touches the working Hub and needs the user.

- [ ] **Step 1:** Final whole-branch review (superpowers:requesting-code-review), fix findings, run `bash scripts/architecture-test.sh` fully. Report known local-only failures separately.
- [ ] **Step 2:** Merge `modular-stage-4` into `main` and push. **Ask the user before pushing.** Wait for CI and check it with `gh run list --limit 1` once; do not poll.
- [ ] **Step 3:** Show the user `git -C <hub> status --short`. The 11 tracked files left from the previous update must be committed first: ask for permission and commit only them. Untracked user files (images, new cards, `.tmp/`) are not ours: ask whether to run with `--allow-dirty` instead of touching them.
- [ ] **Step 4:** `bash scripts/update-installed-hub.sh --dry-run --source . --hub <hub> --without obsidian`. Show the list in simple Russian: removed Obsidian scripts and rules, changed skills and `architecture.md`, new `ai/modules.md`. Apply only after an explicit "да" with `--apply --confirm-plan <sha>`.
- [ ] **Step 5:** Verify:
  - `python3 scripts/hub_release.py drift --source . --hub <hub>` → exit 0;
  - `cat <hub>/ai/modules.md` shows no subscribers;
  - `bash <hub>/scripts/check-all-task-records.sh` passes;
  - the vault's `git status` is unchanged.
- [ ] **Step 6:** Project memory. Add a decision "2026-09-27 — Obsidian is an optional module, disabled in the working Hub": the 2026-08-29 reverse-proposal decision applies only while it is installed; re-enable with `--with obsidian`. Add a changelog entry. Update the `Agent handoff` in `ai/current-task.md`. Ask before closing the task (`hub-task-finish`).

---

## Self-review notes

- Spec coverage: passports (T1), manifest from passports and selection (T2), rules extraction with version bump (T3), events and strict isolation test (T4), boundary check (T5), updater switch, data safety and re-enable (T6), working Hub, decision and CI (T7).
- Required-module refusal is tested in T1 (unit), T2 (preview), and T6 (CLI).
