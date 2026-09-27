import re
import unittest
from pathlib import Path

from scripts.module_passports import install_pairs, load_passports

ROOT = Path(__file__).resolve().parents[1]
NO_OBSIDIAN = ["core", "projects", "tasks", "knowledge", "calendar"]
NO_PLANNING_CALENDAR = ["core", "projects", "tasks"]
PLANNING_CALENDAR_TERMS = re.compile(
    r"hub-calendar|hub-workflows|preview_change|apply_change|read_events|"
    r"snapshot-calendar\.sh|calendar_task_sync\.py|(?i:apple calendar)"
)
CONFIRMATION_SKILLS = ["hub-task-intake", "hub-task-switch", "hub-task-finish"]
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


class PlanningCalendarIsolationTests(unittest.TestCase):
    def test_no_planning_or_calendar_in_core_tasks_projects(self):
        passports = load_passports(ROOT)
        hits = []
        for module_id in NO_PLANNING_CALENDAR:
            for source, _ in install_pairs(ROOT, passports, [module_id]):
                text = (ROOT / source).read_text(encoding="utf-8", errors="replace")
                for match in PLANNING_CALENDAR_TERMS.finditer(text):
                    hits.append(f"{source}: {match.group(0)}")
        self.assertEqual(hits, [])

    def test_task_skills_fire_before_task_confirmation(self):
        for skill in CONFIRMATION_SKILLS:
            text = (ROOT / f"hub-template/ai/skills/{skill}/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("`before-task-confirmation`", text, skill)


if __name__ == "__main__":
    unittest.main()
