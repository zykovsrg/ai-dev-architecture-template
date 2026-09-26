#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("task_records", ROOT / "scripts/task_records.py")
tr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tr)

LINK = "Событие: CAL-1/EV-1 · синхронизировано: 2026-09-22 15:00-17:00"


class SyncFields(unittest.TestCase):
    def test_scheduled_forms(self):
        want = ("2026-09-22 15:00", "2026-09-22 17:00")
        self.assertEqual(tr.parse_scheduled("Запланировано: 2026-09-22 15:00-17:00 (Europe/Kirov)."), want)
        self.assertEqual(tr.parse_scheduled("Запланировано: 2026-09-22 15:00–17:00 (Europe/Kirov)."), want)
        self.assertEqual(tr.parse_scheduled("Запланировано: 2026-09-22 15:00-17:00"), want)
        self.assertIsNone(tr.parse_scheduled("Запланировано: 2026-09-22 (весь день)."))
        self.assertIsNone(tr.parse_scheduled("Status: ready"))

    def test_link(self):
        self.assertEqual(tr.parse_event_link(LINK), {
            "calendar_id": "CAL-1", "event_id": "EV-1",
            "synced_start": "2026-09-22 15:00", "synced_end": "2026-09-22 17:00"})
        self.assertIsNone(tr.parse_event_link("Status: ready"))
        with self.assertRaises(ValueError):
            tr.parse_event_link("Событие: broken")

    def test_future_record_fields(self):
        text = ("# Future Tasks\n\n### FT-20260915-001 — Уточнить\n\nStatus: ready\nDue: 2026-09-23\n"
                "Created: 2026-09-15\nЗапланировано: 2026-09-22 15:00-17:00 (Europe/Kirov).\n" + LINK + "\n")
        [rec] = tr.read_records("demo", "future", text)
        self.assertEqual(rec["scheduled"], ("2026-09-22 15:00", "2026-09-22 17:00"))
        self.assertEqual(rec["event_link"]["event_id"], "EV-1")

    def test_current_record_without_fields(self):
        text = "# Current Task\n\nStatus: active\nTask ID: TASK-demo-20260921-001\n\n## Goal\n\nЦель.\n"
        [rec] = tr.read_records("demo", "current", text)
        self.assertIsNone(rec["scheduled"])
        self.assertIsNone(rec["event_link"])

    def test_malformed_link_rejected_by_strict_read(self):
        text = "# Current Task\n\nStatus: active\nTask ID: TASK-demo-20260921-001\nСобытие: x\n\n## Goal\n\nЦель.\n"
        with self.assertRaises(ValueError):
            tr.read_records("demo", "current", text)


if __name__ == "__main__":
    unittest.main()
