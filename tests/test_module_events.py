import re
import unittest
from pathlib import Path

from scripts.module_passports import install_pairs, load_passports, render_modules_md

ROOT = Path(__file__).resolve().parents[1]
NO_OBSIDIAN = ["core", "projects", "tasks", "knowledge", "calendar"]
NO_PLANNING_CALENDAR = ["core", "projects", "tasks"]
PLANNING_CALENDAR_TERMS = re.compile(
    r"hub-calendar|hub-workflows|preview_change|apply_change|read_events|"
    r"snapshot-calendar\.sh|calendar_task_sync\.py|(?i:apple calendar)"
)
CONFIRMATION_SKILLS = ["hub-task-intake", "hub-task-switch", "hub-task-finish"]
EVENT_SKILLS = ["hub-task-intake", "hub-task-switch", "hub-task-finish", "hub-info-update"]


def _skill_source(root, passports, skill):
    target = f"ai/skills/{skill}/"
    for module_id in passports:
        for source, dest in passports[module_id].installs:
            if dest == target:
                return source.rstrip("/")
    raise AssertionError(f"no module installs skill {skill}")


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
        passports = load_passports(ROOT)
        for skill in EVENT_SKILLS:
            source = _skill_source(ROOT, passports, skill)
            text = (ROOT / source / "SKILL.md").read_text(encoding="utf-8")
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
        passports = load_passports(ROOT)
        for skill in CONFIRMATION_SKILLS:
            source = _skill_source(ROOT, passports, skill)
            text = (ROOT / source / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("`before-task-write`", text, skill)


def event_block(text, event):
    return text.split(f"### {event}\n", 1)[1].split("\n### ", 1)[0]


class LifecycleEventTests(unittest.TestCase):
    def skill(self, name):
        passports = load_passports(ROOT)
        source = _skill_source(ROOT, passports, name)
        return (ROOT / source / "SKILL.md").read_text(encoding="utf-8")

    def test_task_finish_fires_before_task_close(self):
        text = self.skill("hub-task-finish")
        self.assertIn("`before-task-close`", text)
        self.assertIn("ai/modules.md", text)
        self.assertNotIn("hub-session-review", text)
        self.assertNotIn("hub-knowledge-review", text)
        self.assertLess(text.index("`before-task-close`"), text.index("clearing task context"))

    def test_project_create_fires_after_project_create(self):
        text = self.skill("hub-project-create")
        self.assertIn("`after-project-create`", text)
        self.assertIn("ai/modules.md", text)
        self.assertNotIn("hub-knowledge-", text)

    def test_modules_md_lists_lifecycle_subscribers(self):
        passports = load_passports(ROOT)
        full = render_modules_md(passports, list(passports), ROOT)
        close = event_block(full, "before-task-close")
        self.assertIn("- learning:", close)
        self.assertIn("- knowledge:", close)
        create = event_block(full, "after-project-create")
        self.assertIn("- knowledge:", create)
        self.assertNotIn("- learning:", create)
        slim = [i for i in passports if i not in {"learning", "knowledge"}]
        text = render_modules_md(passports, slim, ROOT)
        self.assertEqual(event_block(text, "before-task-close").strip(), "- —")
        self.assertEqual(event_block(text, "after-project-create").strip(), "- —")


class OptionalActionGateTests(unittest.TestCase):
    def test_overview_gates_actions_of_switchable_modules(self):
        text = (ROOT / "modules/tasks/skills/hub-task-overview/SKILL.md").read_text(encoding="utf-8")
        gate = text.split("Emit an action only when the module that owns it is listed", 1)
        self.assertEqual(len(gate), 2)
        for action, module in (("create_knowledge", "knowledge"), ("update_knowledge", "knowledge"),
                               ("goal_progress", "goals"), ("add_observation", "learning"),
                               ("promote_rule", "learning"), ("retire_rule", "learning")):
            self.assertIn(f"`{action}`", gate[1].split("After envelopes")[0], action)
            self.assertIn(f"`{module}`", gate[1].split("After envelopes")[0], module)


if __name__ == "__main__":
    unittest.main()
