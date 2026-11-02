"""Проверка полного и неполного плана через настоящий командный вход."""
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/validate-day-plan-output.py'
VALID = '## Текущий календарь\n- Встреча.\n## Синхронизация\n- Задача.\n## Просроченные задачи\n- Нет.\n'


class PlanValidationTests(unittest.TestCase):
    def run_plan(self, draft):
        return subprocess.run([sys.executable, str(SCRIPT)], input=draft,
                              text=True, capture_output=True, timeout=10)

    def test_complete_plan_is_accepted(self):
        self.assertEqual(self.run_plan(VALID).returncode, 0)

    def test_extra_section_is_rejected(self):
        self.assertNotEqual(self.run_plan(VALID + '## Лишний раздел\n- Текст.\n').returncode, 0)

    def test_empty_section_is_rejected(self):
        self.assertNotEqual(self.run_plan(VALID.replace('- Задача.\n', '\n')).returncode, 0)

    def test_reordered_sections_are_rejected(self):
        draft = '## Синхронизация\n- Задача.\n## Текущий календарь\n- Встреча.\n## Просроченные задачи\n- Нет.\n'
        self.assertNotEqual(self.run_plan(draft).returncode, 0)
