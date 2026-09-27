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
