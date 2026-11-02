"""Проверяем исполняемый договор двух режимов вывода."""
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/validate-day-plan-output.py'


def validate(headings, reminders=False, bodies=None):
    bodies = bodies or ['Нет записей.'] * len(headings)
    draft = '\n'.join(h + '\n' + body for h, body in zip(headings, bodies))
    return subprocess.run([sys.executable, str(SCRIPT)] + (['--reminders'] if reminders else []),
                          input=draft, capture_output=True, text=True)


class DayPlanValidator(unittest.TestCase):
    def test_reminders_accepts_two_sections_and_rejects_wrong_structure(self):
        headings = ['## Календарь', '## Напоминания']
        self.assertEqual(validate(headings, True).returncode, 0)
        for invalid in [headings[::-1], headings[:1], headings + ['## Синхронизация'], headings + headings[:1]]:
            with self.subTest(invalid=invalid):
                self.assertNotEqual(validate(invalid, True).returncode, 0)

    def test_reminders_rejects_empty_sections(self):
        for bodies in [['', 'Задачи'], ['События', '   ']]:
            with self.subTest(bodies=bodies):
                self.assertNotEqual(validate(['## Календарь', '## Напоминания'], True, bodies).returncode, 0)

    def test_legacy_keeps_three_sections_and_requires_explicit_mode(self):
        self.assertEqual(validate(['## Текущий календарь', '## Синхронизация', '## Просроченные задачи']).returncode, 0)
        self.assertNotEqual(validate(['## Календарь', '## Напоминания']).returncode, 0)
