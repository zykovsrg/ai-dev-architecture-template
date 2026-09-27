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

    def test_install_target_under_projects_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "modules/demo/module.md"
            write(path, PASSPORT.replace(
                "modules/demo/rules.md -> ai/rules/demo.md",
                "modules/demo/rules.md -> projects/x.md",
            ))
            with self.assertRaises(ValueError):
                parse_passport(path)

    def test_install_target_under_dot_local_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "modules/demo/module.md"
            write(path, PASSPORT.replace(
                "modules/demo/rules.md -> ai/rules/demo.md",
                "modules/demo/rules.md -> .local/x",
            ))
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

    def test_modules_md_lists_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "modules/demo/module.md", PASSPORT.replace(
                "- modules/demo/scripts/ -> scripts/\n",
                "- modules/demo/scripts/ -> scripts/\n- modules/demo/skills/ -> ai/skills/\n",
            ))
            write(root / "modules/demo/scripts/demo.sh", "echo\n")
            write(root / "modules/demo/rules.md", "# rules\n")
            write(root / "modules/demo/skills/hub-demo/SKILL.md", "# skill\n")
            write(root / "modules/demo/skills/hub-demo/resources/x.md", "resource\n")
            passports = load_passports(root)
            text = render_modules_md(passports, ["demo"], root=root)
            self.assertIn("## Skills", text)
            self.assertIn("- demo: `hub-demo`", text)

    def test_modules_md_omits_modules_without_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root / "modules/demo/module.md", PASSPORT)
            write(root / "modules/demo/scripts/demo.sh", "echo\n")
            write(root / "modules/demo/rules.md", "# rules\n")
            passports = load_passports(root)
            text = render_modules_md(passports, ["demo"], root=root)
            self.assertIn("## Skills\n\n\n## Events", text)


class RepositoryPassportTests(unittest.TestCase):
    def test_every_spec_module_has_a_passport(self):
        self.assertEqual(set(load_passports(ROOT)), SPEC_MODULES)

    def test_every_template_file_has_exactly_one_owner(self):
        passports = load_passports(ROOT)
        owners = {}
        for module_id in passports:
            for source, _ in install_pairs(ROOT, passports, [module_id]):
                owners.setdefault(source, []).append(module_id)
            for source in passports[module_id].repo_only:
                owners.setdefault(source.rstrip("/"), []).append(module_id)
        distributable = set()
        for base in ("skills", "scripts", "data"):
            for p in (ROOT / "modules").glob(f"*/{base}/**/*"):
                if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                    distributable.add(str(p.relative_to(ROOT)))
        for p in (ROOT / "modules").glob("*/rules.md"):
            distributable.add(str(p.relative_to(ROOT)))
        self.assertEqual(sorted(distributable - set(owners)), [])
        self.assertEqual({s: o for s, o in owners.items() if len(o) > 1}, {})

    def test_dependencies_reference_known_modules(self):
        passports = load_passports(ROOT)
        for p in passports.values():
            for dep in p.depends + p.uses_if_present:
                self.assertIn(dep, passports, f"{p.id} -> {dep}")

    def test_switchable_modules(self):
        passports = load_passports(ROOT)
        self.assertEqual({p.id for p in passports.values() if p.switchable},
                         {"obsidian", "planning", "calendar"})

    def test_after_calendar_change_is_a_known_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "modules/demo/module.md"
            write(path, PASSPORT.replace("after-task-write:", "after-calendar-change:"))
            p = parse_passport(path)
            self.assertEqual(p.subscribes, {"after-calendar-change": "bash scripts/demo.sh --hub <hub>"})

    def test_release_installs_nothing(self):
        self.assertNotIn("release", installable(load_passports(ROOT)))


if __name__ == "__main__":
    unittest.main()
