import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def template(path):
    return (ROOT / "hub-template" / path).read_text(encoding="utf-8")


class LiveHubMergeTests(unittest.TestCase):
    def test_template_keeps_existing_learning_and_adds_session_review(self):
        text = template("ai/architecture.md")
        self.assertIn("## Goal Progress", text)
        self.assertIn("## Self-Learning Workflows", text)
        self.assertIn("hub-session-review", text)
        self.assertIn("snapshot-calendar.sh", text)

    def test_template_workflows_keep_calendar_and_rule_lifecycle(self):
        workflows = template("ai/skills/hub-workflows/SKILL.md")
        calendar = template("ai/skills/hub-calendar/SKILL.md")
        self.assertIn("promote_rule", workflows)
        self.assertIn("retire_rule", workflows)
        self.assertIn("snapshot-calendar.sh", workflows)
        self.assertIn("snapshot-calendar.sh", calendar)


if __name__ == "__main__":
    unittest.main()
