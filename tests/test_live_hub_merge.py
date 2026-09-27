import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def template(path):
    return (ROOT / "hub-template" / path).read_text(encoding="utf-8")


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


class LiveHubMergeTests(unittest.TestCase):
    def test_template_keeps_existing_learning_and_adds_session_review(self):
        goals = source("modules/goals/rules.md")
        learning = source("modules/learning/rules.md")
        planning = source("modules/planning/rules.md")
        self.assertIn("## Goal Progress", goals)
        self.assertIn("## Self-Learning Workflows", learning)
        self.assertIn("hub-session-review", learning)
        self.assertIn("snapshot-calendar.sh", planning)

    def test_template_workflows_keep_calendar_and_rule_lifecycle(self):
        workflows = source("modules/planning/skills/hub-workflows/SKILL.md")
        calendar = source("modules/calendar/skills/hub-calendar/SKILL.md")
        self.assertIn("promote_rule", workflows)
        self.assertIn("retire_rule", workflows)
        self.assertIn("snapshot-calendar.sh", workflows)
        self.assertIn("after-calendar-change", calendar)

    def test_task_close_reviews_before_memory_clear(self):
        finish = template("ai/skills/hub-task-finish/SKILL.md")
        self.assertLess(finish.index("`before-task-close`"), finish.index("clearing task context"))
        learning = source("modules/learning/rules.md")
        self.assertIn("hub-session-review", learning[learning.index("## before-task-close"):])
        self.assertIn("deterministic", finish)


if __name__ == "__main__":
    unittest.main()
