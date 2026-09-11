import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.task_records import read_due, read_project_records, read_records, validate_project_dates


CURRENT = """Status: active
Task ID: TASK-demo-20260909-001
Due: 2026-09-10

## Goal

Write report
"""
FUTURE = """### FT-20260909-001 — Next report

Status: ready
due: 2026-09-11
"""
PAUSED = """### 2026-09-09 — Resume report

Task ID: TASK-demo-20260909-002

Status: paused
"""


class TaskRecordTests(unittest.TestCase):
    def test_accepts_both_due_spellings(self):
        self.assertEqual(read_due(["Due: 2026-09-10"]), "2026-09-10")
        self.assertEqual(read_due(["due: 2026-09-10"]), "2026-09-10")

    def test_rejects_conflicting_or_impossible_dates(self):
        with self.assertRaises(ValueError):
            read_due(["Due: 2026-09-10", "due: 2026-09-11"])
        with self.assertRaises(ValueError):
            read_due(["Due: 2026-02-30"])

    def test_reads_a_future_record_with_canonicalized_due_date(self):
        records = read_records("demo", "future", """### TASK-demo-20260909-001 — Write report

Status: ready
due: 2026-09-10
""")
        self.assertEqual(records[0]["task_id"], "TASK-demo-20260909-001")
        self.assertEqual(records[0]["title"], "Write report")
        self.assertEqual(records[0]["due"], "2026-09-10")

    def test_reads_current_task(self):
        records = read_records("demo", "current", CURRENT)
        self.assertEqual(records[0]["status"], "active")
        self.assertEqual(records[0]["title"], "Write report")

    def test_ignores_unfilled_current_task_template(self):
        records = read_records("demo", "current", """Status: empty
Task ID: TASK-YYYYMMDD-NNN

## Goal

Что нужно изменить.
""")
        self.assertEqual(records, [])

    def test_ignores_unfilled_future_task_template(self):
        records = read_records("demo", "future", """### FT-YYYYMMDD-001 — Task title

Status: idea
""")
        self.assertEqual(records, [])

    def test_reads_paused_task(self):
        records = read_records("demo", "paused", PAUSED)
        self.assertEqual(records[0]["status"], "paused")
        self.assertEqual(records[0]["title"], "Resume report")

    def test_validates_all_project_due_dates_in_one_call(self):
        due_dates = validate_project_dates(CURRENT.replace("Due: 2026-09-10\n", ""), FUTURE, PAUSED)
        self.assertEqual(due_dates, {"current": None, "future": "2026-09-11", "paused": None})

    def test_read_project_records_combines_all_kinds(self):
        records = read_project_records("demo", CURRENT, FUTURE, PAUSED)
        self.assertEqual([row["source_kind"] for row in records], ["current", "future", "paused"])
        self.assertEqual([row["task_id"] for row in records], [
            "TASK-demo-20260909-001", "FT-20260909-001", "TASK-demo-20260909-002"
        ])

    def test_read_project_records_preserves_per_kind_validation(self):
        with self.assertRaises(ValueError):
            read_project_records("demo", CURRENT.replace("Status: active", "Status: nonsense"), FUTURE, PAUSED)
        with self.assertRaises(ValueError):
            read_project_records("demo", CURRENT, FUTURE.replace("Status: ready", "Status: nonsense"), PAUSED)
        with self.assertRaises(ValueError):
            read_project_records("demo", CURRENT, FUTURE, PAUSED.replace("Status: paused", "Status: active"))

    def test_three_file_cli_returns_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / "current.md"
            future = root / "future.md"
            paused = root / "paused.md"
            current.write_text(CURRENT, encoding="utf-8")
            future.write_text(FUTURE, encoding="utf-8")
            paused.write_text(PAUSED, encoding="utf-8")
            result = subprocess.run([
                sys.executable, "scripts/task_records.py",
                "--project-id", "demo",
                "--current-file", str(current),
                "--future-file", str(future),
                "--paused-file", str(paused),
            ], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(len(payload["records"]), 3)


if __name__ == "__main__":
    unittest.main()
