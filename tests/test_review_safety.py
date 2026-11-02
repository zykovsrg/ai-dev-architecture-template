"""Доставка правил и реальный отказ обновления; не доказательство поведения модели."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.hub_release import apply, preview

ROOT = Path(__file__).resolve().parents[1]


class ReviewSafetyTests(unittest.TestCase):
    def installed_section(self, heading):
        with tempfile.TemporaryDirectory() as temporary:
            hub = Path(temporary).resolve() / '_ai-hub'
            hub.mkdir()
            plan = preview(ROOT, hub)
            apply(ROOT, hub, plan['plan_sha256'])
            text = (hub / 'ai/architecture.md').read_text()
        return text.partition(heading)[2].partition('\n## ')[0]

    def test_fresh_install_distinguishes_delivery_from_working_behavior(self):
        section = self.installed_section('## Проверка результата перед сообщением о готовности')
        self.assertIn('Доставка изменения, наличие инструкции и проверка поведения — разные результаты.', section)
        self.assertIn('Не объявляйте работу проверенной по одному наличию файлов', section)
        self.assertIn('Если фактическое поведение проверить нельзя, назовите ограничение', section)

    def test_fresh_install_requires_user_decision_after_protected_refusal(self):
        section = self.installed_section('## Защитный отказ обновления')
        self.assertIn('Никогда самостоятельно не добавляйте --allow-dirty', section)
        self.assertIn('назовите причину и запросите решение пользователя', section)
        self.assertIn('Принятие задачи не разрешает обход защиты.', section)

    def test_fresh_install_checks_background_dependencies_before_cleanup(self):
        section = self.installed_section('## Фоновые зависимости программы перед очисткой')
        self.assertIn('launchd, crontab, автоматизации «Кодекса»', section)
        self.assertIn('Недоступная проверка означает неизвестность, а не отсутствие зависимости.', section)
        self.assertIn('не разрешает останавливать службы или удалять данные', section)

    def test_dirty_update_preserves_files_and_requests_user_decision(self):
        with tempfile.TemporaryDirectory() as temporary:
            hub = Path(temporary).resolve() / '_ai-hub'
            hub.mkdir()
            plan = preview(ROOT, hub)
            apply(ROOT, hub, plan['plan_sha256'])
            environment = os.environ.copy()
            environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
                               GIT_CONFIG_COUNT='0', GIT_TEMPLATE_DIR=str(hub / 'empty-template'))
            (hub / 'empty-template').mkdir()
            native = Path('/Library/Developer/CommandLineTools/usr/bin/git')
            git = str(native) if native.is_file() else shutil.which('git')
            self.assertIsNotNone(git)
            environment['PATH'] = str(Path(git).parent) + os.pathsep + environment['PATH']
            subprocess.run([git, 'init', '-q', str(hub)], env=environment, check=True,
                           capture_output=True, text=True)
            sentinel = hub / 'AGENTS.md'
            sentinel.write_text(sentinel.read_text() + '\nМестная несохранённая работа.\n')
            before = sentinel.read_bytes()
            plan = preview(ROOT, hub)
            result = subprocess.run(['bash', str(ROOT / 'scripts/update-installed-hub.sh'),
                                     '--source', str(ROOT), '--hub', str(hub), '--apply',
                                     '--confirm-plan', plan['plan_sha256']],
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn('Hub working tree is dirty', result.stderr)
            self.assertIn('ask the user', result.stderr)
            self.assertNotIn('--allow-dirty', result.stderr)
            self.assertEqual(sentinel.read_bytes(), before)
