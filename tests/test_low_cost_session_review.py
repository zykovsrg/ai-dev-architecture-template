import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "hub-template/ai/skills/hub-session-review/SKILL.md"
FINISH = ROOT / "hub-template/ai/skills/hub-task-finish/SKILL.md"


def section(text, heading):
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError(f"missing section: {heading}")
    return match.group(1)


def compact(text):
    return " ".join(text.split())


class LowCostSessionReviewTests(unittest.TestCase):
    def test_deterministic_validation_precedes_semantic_review(self):
        cost = compact(section(REVIEW.read_text(encoding="utf-8"), "Cost control"))
        deterministic = cost.index("Run deterministic checks")
        semantic = cost.index("For semantic review")
        self.assertLess(deterministic, semantic)

    def test_semantic_review_defaults_low_cost_and_escalates_conditionally(self):
        cost = compact(section(REVIEW.read_text(encoding="utf-8"), "Cost control"))
        self.assertIn("use Luna by default", cost)
        self.assertRegex(
            cost,
            r"Use Terra only when Luna .*ambiguous.*material risk",
        )

    def test_review_keeps_evidence_bounded(self):
        review = compact(REVIEW.read_text(encoding="utf-8"))
        self.assertIn("smallest available evidence range", review)
        self.assertIn("Never expand a partial history automatically", review)
        self.assertIn("read only the selected session or range", review)

    def test_closure_runs_checks_and_review_before_context_cleanup(self):
        finish = compact(FINISH.read_text(encoding="utf-8"))
        deterministic = finish.index("Run the deterministic task-record and review checks before any model call")
        review = finish.index("run `hub-session-review`")
        cleanup = finish.index("cleanup", review)
        self.assertLess(deterministic, review)
        self.assertLess(review, cleanup)
        self.assertIn("A review-write failure leaves the task open and its context intact", finish)


if __name__ == "__main__":
    unittest.main()
