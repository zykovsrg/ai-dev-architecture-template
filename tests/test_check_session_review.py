#!/usr/bin/env python3
"""Regression checks for the strict session-review format."""

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "modules/learning/scripts/check-session-review.py"


class SessionReviewCheckerTests(unittest.TestCase):
    def test_strict_mode_accepts_complete_valid_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "seo-content-creator"
            review = project / "ai/session-reviews/review.md"
            review.parent.mkdir(parents=True)
            review.write_text(
                """# Session review

Review ID: SR-test-valid-001
Project ID: seo-content-creator
Task ID: none
Session ID: unavailable
Trigger: user-request
Coverage: complete
Evidence range: every visible message in the selected session
Missing evidence: none
Chronology audit: every available message reviewed
Claim action audit: no material claims
Prior review audit: none found
Result: no-issue-observed
Supplements: none

## Goal and result

The checked session contains no observed issue.

## Findings

none

## Improvement proposals

none

## Follow-up

none
""",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    "python3", str(CHECKER), "--project", str(project), "--file", str(review),
                    "--require-chronology",
                ],
                text=True,
                capture_output=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
