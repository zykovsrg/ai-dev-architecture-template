import re
import unittest
from pathlib import Path

from scripts.module_passports import install_pairs, load_passports

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "modules/core/data/ai/architecture.md"
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
        for rel in ("modules/core/data/ai/architecture.md", "modules/core/data/CLAUDE.md", "modules/core/data/AGENTS.md"):
            hits = phrase.findall((ROOT / rel).read_text(encoding="utf-8"))
            self.assertLessEqual(len(hits), 1, rel)


if __name__ == "__main__":
    unittest.main()
