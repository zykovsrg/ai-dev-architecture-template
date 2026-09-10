import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts" / "check-session-review.py"


def document(*, result="no-issue-observed", findings="none", proposals="none", coverage="complete", missing="none"):
    return f"""# Session review

Review ID: 20260909T120000Z-task-1-deadbeef
Project ID: demo
Task ID: TASK-demo-20260909-001
Session ID: unavailable
Trigger: task-close
Coverage: {coverage}
Evidence range: current visible session
Missing evidence: {missing}
Result: {result}
Supplements: none

## Goal and result

Close one verified task.

## Findings

{findings}

## Improvement proposals

{proposals}

## Follow-up

none
"""


class SessionReviewValidationTests(unittest.TestCase):
    def run_checker(self, content):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "demo"
            review_dir = project / "ai" / "session-reviews"
            review_dir.mkdir(parents=True)
            review = review_dir / "review.md"
            review.write_text(content, encoding="utf-8")
            return subprocess.run(
                ["python3", str(CHECKER), "--project", str(project), "--file", str(review)],
                text=True,
                capture_output=True,
                check=False,
            )

    def test_accepts_a_clean_complete_review(self):
        result = self.run_checker(document())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_complete_coverage_with_missing_evidence(self):
        result = self.run_checker(document(missing="opening user request"))
        self.assertNotEqual(result.returncode, 0)

    def test_rejects_issue_without_evidence(self):
        result = self.run_checker(document(
            result="issues-found",
            findings="""### F1
Observation: agent changed an unrequested file
Evidence: none
Cause: observed
Impact: extra work""",
        ))
        self.assertNotEqual(result.returncode, 0)

    def test_rejects_a_symlinked_review_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "demo"
            (project / "ai").mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            (project / "ai" / "session-reviews").symlink_to(outside, target_is_directory=True)
            (outside / "review.md").write_text(document(), encoding="utf-8")
            review = project / "ai" / "session-reviews" / "review.md"
            result = subprocess.run(
                ["python3", str(CHECKER), "--project", str(project), "--file", str(review)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(result.returncode, 0)

    def test_accepts_an_issue_with_a_linked_proposal(self):
        result = self.run_checker(document(
            result="issues-found",
            findings="""### F1
Observation: agent changed an unrequested file
Evidence: visible user correction after the edit
Cause: observed
Impact: extra work""",
            proposals="""### P1
Finding: F1
Scope: hub-template/ai/skills/hub-task-finish/SKILL.md
Change: require scope check before edits
Rationale: prevents repeat extra edits
Acceptance test: review a comparable session
Recovery: revert this wording
Disposition: proposed""",
        ))
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
