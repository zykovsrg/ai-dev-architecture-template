import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "modules/learning/scripts/review_proposals.py"

REVIEW = """# Session review

Review ID: R1
Result: issues-found

## Findings

### F1
Observation: secret detail that must not leak.

## Improvement proposals

### P1
Finding: F1
Scope: project
Change: always check the thing
  before reporting success.
Disposition: proposed

### P2
Finding: F1
Change: already done.
Disposition: implemented

### P3
Finding: F1
Change: approved but not built.
Disposition: accepted

## Follow-up

none
"""


def registry_entry(project_id, path, status="active"):
    return f"## {project_id}\nName: {project_id}\nStatus: {status}\nPath: {path}\n\n"


class ReviewProposalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.hub = Path(self.tmp.name).resolve()
        (self.hub / "ai").mkdir()
        registry = "# Project Registry\n\n"
        for project_id, status in (("alpha", "active"), ("old", "archived")):
            reviews = self.hub / "projects" / project_id / "ai/session-reviews"
            reviews.mkdir(parents=True)
            (reviews / "2026-09-10-closure.md").write_text(REVIEW, encoding="utf-8")
            registry += registry_entry(project_id, self.hub / "projects" / project_id, status)
        (self.hub / "ai/project-registry.md").write_text(registry, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--hub", str(self.hub), *args],
                              capture_output=True, text=True, check=False)

    def listed(self):
        result = self.run_script("list", "--until", "2026-10-01")
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_lists_open_proposals_of_active_projects_only(self):
        items = self.listed()
        self.assertEqual([(i["project"], i["proposal"], i["disposition"]) for i in items],
                         [("alpha", "P1", "proposed"), ("alpha", "P3", "accepted")])
        first = items[0]
        self.assertEqual(first["review"], "ai/session-reviews/2026-09-10-closure.md")
        self.assertEqual(first["change"], "always check the thing before reporting success.")
        self.assertEqual(first["age_days"], 21)
        self.assertNotIn("secret", json.dumps(items))

    def test_set_changes_only_the_disposition_line(self):
        path = self.hub / "projects/alpha/ai/session-reviews/2026-09-10-closure.md"
        result = self.run_script("set", "--project", "alpha", "--review", "ai/session-reviews/2026-09-10-closure.md",
                                 "--proposal", "P1", "--decision", "rejected")
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = REVIEW.replace("  before reporting success.\nDisposition: proposed",
                                  "  before reporting success.\nDisposition: rejected")
        self.assertEqual(path.read_text(encoding="utf-8"), expected)
        self.assertEqual([i["proposal"] for i in self.listed()], ["P3"])

    def test_set_refuses_paths_outside_session_reviews_and_inactive_projects(self):
        for project, review in (("alpha", "ai/current-task.md"), ("alpha", "ai/session-reviews/../x.md"),
                                ("old", "ai/session-reviews/2026-09-10-closure.md"),
                                ("missing", "ai/session-reviews/2026-09-10-closure.md")):
            result = self.run_script("set", "--project", project, "--review", review,
                                     "--proposal", "P1", "--decision", "accepted")
            self.assertNotEqual(result.returncode, 0, (project, review))

    def test_set_rejects_unknown_decision_and_proposal(self):
        base = ("set", "--project", "alpha", "--review", "ai/session-reviews/2026-09-10-closure.md")
        self.assertNotEqual(self.run_script(*base, "--proposal", "P1", "--decision", "maybe").returncode, 0)
        self.assertNotEqual(self.run_script(*base, "--proposal", "P9", "--decision", "accepted").returncode, 0)


if __name__ == "__main__":
    unittest.main()
