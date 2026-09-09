import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LowCostSessionReviewTests(unittest.TestCase):
    def test_workflows_define_a_low_cost_review_path(self):
        review = (ROOT / "hub-template/ai/skills/hub-session-review/SKILL.md").read_text(encoding="utf-8")
        finish = (ROOT / "hub-template/ai/skills/hub-task-finish/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Luna", review)
        self.assertIn("Terra", review)
        self.assertIn("before any model call", finish)


if __name__ == "__main__":
    unittest.main()
