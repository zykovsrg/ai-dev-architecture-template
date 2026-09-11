import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "hub-template/ai/skills/hub-workflows/SKILL.md"
LIFECYCLE = ROOT / "hub-template/ai/skills/hub-workflows/resources/learning-lifecycle.md"
LEARNING_ACTIONS = {"goal_progress", "add_observation", "promote_rule", "retire_rule"}


class HubLearningContractTests(unittest.TestCase):
    def test_proposal_actions_cover_learning_lifecycle(self):
        text = SKILL.read_text(encoding="utf-8")
        match = re.search(r"^action: <([^>]+)>$", text, re.MULTILINE)
        self.assertIsNotNone(match, "canonical proposal action enum is missing")
        declared = set(match.group(1).split("|"))
        self.assertTrue(LEARNING_ACTIONS <= declared, LEARNING_ACTIONS - declared)

    def test_proposal_display_keeps_friction_pending(self):
        text = SKILL.read_text(encoding="utf-8")
        lifecycle = LIFECYCLE.read_text(encoding="utf-8")
        self.assertNotIn("marks that friction cache\nconsumed", text)
        self.assertIn("proposal shown → still pending → accepted/rejected → resolved", lifecycle)
        self.assertIn("Showing a proposal never consumes it", lifecycle)

    def test_referenced_learning_actions_are_declared(self):
        text = SKILL.read_text(encoding="utf-8")
        match = re.search(r"^action: <([^>]+)>$", text, re.MULTILINE)
        self.assertIsNotNone(match)
        declared = set(match.group(1).split("|"))
        referenced = set(re.findall(r"`(goal_progress|add_observation|promote_rule|retire_rule)`", text))
        self.assertEqual(referenced, LEARNING_ACTIONS)
        self.assertTrue(referenced <= declared, referenced - declared)


if __name__ == "__main__":
    unittest.main()
