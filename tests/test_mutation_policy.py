"""Проверки доставки общего правила; поведение агента они не доказывают."""
from pathlib import Path
import tempfile
import unittest
from scripts.hub_release import apply, preview

ROOT = Path(__file__).resolve().parents[1]
HEADING = '## Мутационное подтверждение новых тестов'
SCOPE = 'Любой новый тест Хаба, модулей и проектов'


class MutationPolicyTests(unittest.TestCase):
    def test_shared_architecture_requires_each_new_test(self):
        text = (ROOT / 'modules/core/data/ai/architecture.md').read_text()
        self.assertIn(HEADING, text)
        section = text.split(HEADING, 1)[1].split('\n## ', 1)[0]
        for phrase in (SCOPE, 'каждый новый тест отдельно', 'пройти на корректном варианте',
                       'упасть при намеренной ошибке', 'Сбой окружения', 'временной копии'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)

    def test_agent_entries_point_to_shared_policy(self):
        for name in ('AGENTS.md', 'CLAUDE.md'):
            text = (ROOT / 'modules/core/data' / name).read_text()
            with self.subTest(name=name):
                self.assertIn('Каждый новый тест подтверждайте мутацией', text)
                self.assertIn('ai/architecture.md', text)

    def test_project_creation_inherits_policy_without_copying_it(self):
        text = (ROOT / 'modules/projects/skills/hub-project-create/SKILL.md').read_text()
        self.assertIn('Новый проект наследует правило мутационного подтверждения тестов', text)
        self.assertIn('не создавайте отдельную копию правила', text)

    def test_fresh_hub_install_receives_policy_and_creation_rule(self):
        with tempfile.TemporaryDirectory() as temporary:
            hub = Path(temporary).resolve() / '_ai-hub'
            hub.mkdir()
            plan = preview(ROOT, hub)
            apply(ROOT, hub, plan['plan_sha256'])
            self.assertIn(HEADING, (hub / 'ai/architecture.md').read_text())
            self.assertIn('Каждый новый тест подтверждайте мутацией', (hub / 'AGENTS.md').read_text())
            self.assertIn('Новый проект наследует правило мутационного подтверждения тестов',
                          (hub / 'ai/skills/hub-project-create/SKILL.md').read_text())
            self.assertFalse((hub / 'projects/demo/AGENTS.md').exists())
