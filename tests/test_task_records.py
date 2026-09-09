import unittest

from scripts.task_records import read_due


class TaskRecordTests(unittest.TestCase):
    def test_accepts_both_due_spellings(self):
        self.assertEqual(read_due(["Due: 2026-09-10"]), "2026-09-10")
        self.assertEqual(read_due(["due: 2026-09-10"]), "2026-09-10")

    def test_rejects_conflicting_or_impossible_dates(self):
        with self.assertRaises(ValueError):
            read_due(["Due: 2026-09-10", "due: 2026-09-11"])
        with self.assertRaises(ValueError):
            read_due(["Due: 2026-02-30"])


if __name__ == "__main__":
    unittest.main()
