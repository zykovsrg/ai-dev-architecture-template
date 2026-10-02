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

    def test_schedule_with_comment(self):
        self.assertEqual(records.parse_scheduled("Запланировано: 2026-10-02 15:45-16:00 (Europe/Kirov), по дороге."), ("2026-10-02 15:45", "2026-10-02 16:00"))

    def test_legacy_start_only_is_readable_without_inventing_end(self):
        self.assertIsNone(records.parse_scheduled("Запланировано: 2026-09-18 14:00 (Europe/Kirov)."))
        with self.assertRaises(ValueError):
            records.parse_scheduled("Запланировано: 2026-09-18 25:00 (Europe/Kirov).")

    def test_valid_leap_day(self):
        self.assertEqual(records.parse_scheduled("Запланировано: 2028-02-29 15:00-17:00"), ("2028-02-29 15:00", "2028-02-29 17:00"))
