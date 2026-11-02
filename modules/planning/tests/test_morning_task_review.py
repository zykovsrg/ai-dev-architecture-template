"""Договор утреннего разбора: решение задачи, видимость и границы доступа."""
import unittest
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def text(path):
    return ' '.join((REPO / path).read_text(encoding='utf-8').split())


def section(path, heading):
    raw = (REPO / path).read_text(encoding='utf-8')
    assert heading in raw, f'Нет обязательного раздела: {heading}'
    body = raw.split(heading, 1)[1]
    return ' '.join(re.split(r'\n## ', body, maxsplit=1)[0].split())


class MorningTaskReviewTests(unittest.TestCase):
    def test_morning_review_uses_one_session_scan(self):
        day = text('modules/planning/skills/hub-workflows/resources/day-plan.md')
        review = section('modules/planning/skills/hub-workflows/resources/day-plan.md', '## Утренняя проверка текущих задач')
        for phrase in ('каждый критерий', 'каноническ', 'прямое подтверждение пользователя',
                       'на паузу', 'изменённые сегодня', 'hub-session-scan'):
            self.assertIn(phrase.casefold(), review.casefold())
        self.assertIn('Не выполняйте перед ним второй отдельный обход текущих задач', review)

    def test_group_plan_does_not_review_other_projects(self):
        review = section('modules/planning/skills/hub-workflows/resources/day-plan.md', '## Утренняя проверка текущих задач')
        self.assertIn('в области запроса', review)
        self.assertIn('группового плана', review)
        self.assertIn('--group', review)

    def test_pause_keeps_identity_and_calendar_without_false_completion(self):
        day = text('modules/planning/skills/hub-workflows/resources/day-plan.md')
        review = section('modules/planning/skills/hub-workflows/resources/day-plan.md', '## Утренняя проверка текущих задач')
        for phrase in ('Task ID', 'Due:', 'Запланировано:', 'Событие:',
                       'не удаляет событие', 'недостаточн', 'будущие этапы',
                       'просмотра и явного согласия', 'До согласия не закрывайте'):
            self.assertIn(phrase.casefold(), review.casefold())

    def test_undated_tasks_are_concrete_and_visible_in_existing_output(self):
        day = text('modules/planning/skills/hub-workflows/resources/day-plan.md')
        body = section('modules/planning/skills/hub-workflows/resources/day-plan.md', '## Вывод')
        for phrase in ('до первых пяти', 'название', 'проект', 'приостановленные',
                       'рабочие и личные', 'Не назначайте срок', 'все открытые'):
            self.assertIn(phrase, body)
        self.assertIn('## Календарь', body)
        self.assertIn('## Напоминания', body)

    def test_morning_permissions_do_not_open_project_history_or_memory(self):
        overview = text('modules/tasks/skills/hub-task-overview/SKILL.md')
        finish = text('modules/tasks/skills/hub-task-finish/SKILL.md')
        rules = text('modules/tasks/rules.md')
        for body in (overview, finish, rules):
            self.assertIn('утренней проверки', body)
            self.assertIn('трёх канонических файлов задач', body)
            self.assertIn('без отдельного подтверждения', body)
        self.assertIn('не разрешает чтение журналов', overview)


if __name__ == '__main__':
    unittest.main()
