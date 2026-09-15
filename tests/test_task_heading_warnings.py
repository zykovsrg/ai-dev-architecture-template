import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from task_records import read_records, unrecognized_headings  # noqa: E402


FUTURE = """## Future tasks

### FT-YYYYMMDD-001 — Task title

### FT-20260915-001 — Recognized

Status: ready

### Missing identifier

Status: ready
"""
PAUSED = """## Paused tasks

### YYYY-MM-DD — Task title

### Missing pause date

Task ID: FT-20260915-002
Status: paused
"""


class TaskHeadingWarningTests(unittest.TestCase):
    def make_hub(self, root: Path) -> Path:
        hub = root / "hub"
        project = hub / "projects/demo"
        (hub / "ai").mkdir(parents=True)
        (project / "ai").mkdir(parents=True)
        (hub / "ai/project-registry.md").write_text(
            f"## demo\nStatus: active\nPath: {project}\n", encoding="utf-8"
        )
        (project / "ai/current-task.md").write_text("# Current Task\n\nStatus: empty\n", encoding="utf-8")
        (project / "ai/future-tasks.md").write_text(FUTURE, encoding="utf-8")
        (project / "ai/paused-tasks.md").write_text(PAUSED, encoding="utf-8")
        return hub

    def test_reports_skipped_headings_but_not_template_examples(self):
        self.assertEqual(unrecognized_headings("future", FUTURE.splitlines()), [(9, "### Missing identifier")])
        self.assertEqual(unrecognized_headings("paused", PAUSED.splitlines()), [(5, "### Missing pause date")])
        self.assertEqual(unrecognized_headings("current", ["### Anything"]), [])

    def test_index_warns_on_stderr_and_still_succeeds(self):
        with tempfile.TemporaryDirectory() as temp:
            hub = self.make_hub(Path(temp))
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/read-compact-task-index.py"), "--hub", str(hub)],
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("demo ai/future-tasks.md:9: ### Missing identifier", result.stderr)
        self.assertIn("demo ai/paused-tasks.md:5: ### Missing pause date", result.stderr)
        self.assertNotIn("Task title", result.stderr)

    def test_full_record_check_fails_on_skipped_heading(self):
        with tempfile.TemporaryDirectory() as temp:
            hub = self.make_hub(Path(temp))
            check = ["bash", str(ROOT / "scripts/check-all-task-records.sh"), "--hub", str(hub)]
            self.assertNotEqual(subprocess.run(check, capture_output=True, check=False).returncode, 0)
            future = hub / "projects/demo/ai/future-tasks.md"
            paused = hub / "projects/demo/ai/paused-tasks.md"
            future.write_text(FUTURE.replace("### Missing identifier", "### FT-20260915-003 — Missing identifier"), encoding="utf-8")
            paused.write_text(PAUSED.replace("### Missing pause date", "### 2026-09-15 — Missing pause date"), encoding="utf-8")
            self.assertEqual(subprocess.run(check, capture_output=True, check=False).returncode, 0)

    def test_paused_due_after_pause_metadata_is_read(self):
        text = "### 2026-09-05 — Paused\n\nTask ID: TASK-demo-20260901-001\nStatus: paused\n\nPaused: 2026-09-05\n\ndue: 2026-09-15\n"
        compact = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); from task_records import read_records_lines;"
             "print(read_records_lines('demo', 'paused', sys.stdin)[0]['due'])", str(ROOT / "scripts")],
            input=text, capture_output=True, text=True, check=True,
        )
        self.assertEqual(compact.stdout.strip(), "2026-09-15")
        self.assertEqual(read_records("demo", "paused", text)[0]["due"], "2026-09-15")


if __name__ == "__main__":
    unittest.main()
