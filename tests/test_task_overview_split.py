import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "hub-template/ai/skills"
PLANNING_SKILLS = ROOT / "modules/planning/skills"


def read(path):
    return path.read_text(encoding="utf-8")


class TaskOverviewSplitTests(unittest.TestCase):
    def test_overview_skill_owns_contract_and_capture(self):
        text = read(SKILLS / "hub-task-overview/SKILL.md")
        self.assertIn("## Proposal envelope", text)
        self.assertIn("resources/capture.md", text)
        self.assertTrue((SKILLS / "hub-task-overview/resources/capture.md").is_file())

    def test_workflows_delegates_contract(self):
        text = read(PLANNING_SKILLS / "hub-workflows/SKILL.md")
        self.assertNotIn("## Proposal envelope", text)
        self.assertIn("`hub-task-overview`", text)

    def test_router_uses_overview_and_modules(self):
        text = read(SKILLS / "hub-project-router/SKILL.md")
        self.assertIn("`hub-task-overview`", text)
        self.assertIn("ai/modules.md", text)

    def test_tasks_passport_installs_overview(self):
        text = read(ROOT / "modules/tasks/module.md")
        self.assertIn("hub-template/ai/skills/hub-task-overview/ -> ai/skills/hub-task-overview/", text)


if __name__ == "__main__":
    unittest.main()
