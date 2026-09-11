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


if __name__ == "__main__":
    unittest.main()
