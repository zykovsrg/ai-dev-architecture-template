import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "modules/tasks/scripts/task_records.py"
spec = importlib.util.spec_from_file_location("schedule_records", path)
records = importlib.util.module_from_spec(spec)
spec.loader.exec_module(records)

class ScheduleValidation(unittest.TestCase):
    def test_bad_schedules_raise(self):
        for span in ("2026-99-99 15:00-17:00", "2026-09-22 25:70-17:00", "2026-09-22 17:00-15:00", "2026-09-22 15:00-15:00", "tomorrow"):
            with self.subTest(span=span), self.assertRaises(ValueError):
                records.parse_scheduled("Запланировано: " + span)

    def test_bad_link_date_raises(self):
        with self.assertRaises(ValueError):
            records.parse_event_link("Событие: CAL/EV · синхронизировано: 2026-99-99 15:00-17:00")

    def test_all_day_legacy_date_is_validated(self):
        self.assertIsNone(records.parse_scheduled("Запланировано: 2026-09-22 (весь день)."))
        with self.assertRaises(ValueError):
            records.parse_scheduled("Запланировано: 2026-99-99 (весь день).")

    def test_valid_leap_day(self):
        self.assertEqual(records.parse_scheduled("Запланировано: 2028-02-29 15:00-17:00"), ("2028-02-29 15:00", "2028-02-29 17:00"))
