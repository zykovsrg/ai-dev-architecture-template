import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "hub-template/ai/skills/hub-workflows/SKILL.md"
RESOURCE_DIR = SKILL.parent / "resources"
RESOURCES = {
    "day-plan": "day-plan.md",
    "evening-review": "evening-review.md",
    "weekly-review": "weekly-review.md",
    "capture": "capture.md",
}


class HubWorkflowProgressiveDisclosureTests(unittest.TestCase):
    def test_scenario_resources_exist_and_are_referenced(self):
        core = SKILL.read_text(encoding="utf-8")
        for scenario, filename in RESOURCES.items():
            path = RESOURCE_DIR / filename
            self.assertTrue(path.is_file(), filename)
            self.assertIn(f"resources/{filename}", core)
            text = path.read_text(encoding="utf-8")
            self.assertIn("core `SKILL.md`", text)
            self.assertIn(scenario, text)

    def test_common_authority_stays_in_core(self):
        core = SKILL.read_text(encoding="utf-8")
        for phrase in (
            "## Personal-assistant scope",
            "## Fixed sequence",
            "## Proposal envelope",
            "## Confirmation boundary",
            "Never write or apply a proposal automatically",
            "scripts/read-compact-task-index.py",
        ):
            self.assertIn(phrase, core)

    def test_detailed_scenario_formats_leave_core(self):
        core = SKILL.read_text(encoding="utf-8")
        for phrase in (
            "### Day plan format",
            "### Evening review format",
            "### Weekly review format",
            "## Capture rules",
            "## Текущий календарь",
            "## Сегодняшний календарь",
            "## Архипроекты",
        ):
            self.assertNotIn(phrase, core)

    def test_learning_state_machine_stays_in_its_resource(self):
        core = SKILL.read_text(encoding="utf-8")
        evening = (RESOURCE_DIR / "evening-review.md").read_text(encoding="utf-8")
        lifecycle = (RESOURCE_DIR / "learning-lifecycle.md").read_text(encoding="utf-8")
        self.assertIn("resources/learning-lifecycle.md", core)
        self.assertIn("resources/learning-lifecycle.md", evening)
        for invariant in ("accepted: journal_append", "rejected: no_journal_append", "append_failure: pending"):
            self.assertIn(invariant, lifecycle)
            self.assertNotIn(invariant, evening)

    def test_dated_day_plan_actions_pair_task_and_timed_event(self):
        day_plan = (RESOURCE_DIR / "day-plan.md").read_text(encoding="utf-8")
        for phrase in (
            "relative and explicit dates",
            "30-minute free interval",
            "Запланировано: YYYY-MM-DD HH:MM-HH:MM",
            "explicit interval unchanged",
            "past date does not infer completion",
            "one confirmation may approve only that exact pair",
        ):
            self.assertIn(phrase, day_plan)


if __name__ == "__main__":
    unittest.main()
