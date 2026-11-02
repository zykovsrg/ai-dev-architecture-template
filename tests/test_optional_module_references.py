"""Обязательные модули упоминают необязательные только с условием их установки."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Метки файлов и инструментов необязательных модулей. Простое упоминание плана дня
# или календаря как понятия — не ссылка: оно ничего не вызывает.
OPTIONAL = {
    'calendar': re.compile(r'ai/rules/calendar\.md|hub-calendar|read_events|preview_change|apply_change|'
                           r'snapshot-calendar\.sh'),
    'planning': re.compile(r'reminders_[a-z_]+\.py|reminders-sync\.json|ai/rules/planning\.md|hub-workflows|'
                           r'calendar_task_sync\.py|reminders-project-create\.md|«Напоминани|'
                           r'resources/(day-plan|evening-review|weekly-review)\.md'),
    'learning': re.compile(r'hub-session-scan|hub-session-review|open_task_check\.py|session_[a-z_]+\.py|'
                           r'ai/learning/|learned-rules'),
    'knowledge': re.compile(r'ai/rules/knowledge\.md|hub-knowledge-|hub-info-update'),
    'goals': re.compile(r'hub-goal-progress|count-goal-progress|ai/goals\.md|goal-log'),
}


def units(path, text):
    # Отдельный ресурс вызывается из одного условного места и проверяется целиком;
    # основные файлы проверяются по абзацам.
    if 'resources' in path.parts:
        return [text]
    # Заголовок раздела сам ничего не вызывает; условие стоит в первом абзаце раздела.
    return ['\n'.join(line for line in block.splitlines() if not line.startswith('#'))
            for block in text.split('\n\n')]


def guarded(module, text):
    # Условие называет именно этот модуль.
    return any(phrase in text for phrase in (f'`{module}` указан в `ai/modules.md`', f'установлен `{module}`'))


class OptionalModuleReferenceTests(unittest.TestCase):
    def test_required_modules_guard_optional_references(self):
        for module in ('core', 'projects', 'tasks'):
            for path in sorted((ROOT / 'modules' / module).rglob('*.md')):
                if path.name == 'module.md':
                    continue
                for unit in units(path, path.read_text(encoding='utf-8')):
                    compact = ' '.join(unit.split())
                    for optional, pattern in OPTIONAL.items():
                        found = pattern.search(unit)
                        if found:
                            with self.subTest(path=str(path.relative_to(ROOT)), label=found.group()):
                                self.assertTrue(guarded(optional, compact), unit)


if __name__ == '__main__':
    unittest.main()
