import unittest

from scripts.task_records import read_due, read_records


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


if __name__ == "__main__":
    unittest.main()
