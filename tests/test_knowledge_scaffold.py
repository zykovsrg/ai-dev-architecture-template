"""Проверка совместимости создаваемого шаблона с форматом знаний."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class KnowledgeScaffoldTests(unittest.TestCase):
    def test_new_record_template_has_all_review_metadata(self):
        skill = (ROOT / 'modules/knowledge/skills/hub-knowledge-enable/SKILL.md').read_text()
        section = skill.split('### knowledge/record-template.md', 1)[1]
        template = re.search(r'```markdown\n(.*?)\n```', section, re.S).group(1)
        frontmatter = re.search(r'^---\n(.*?)\n---', template, re.S).group(1)
        fields = dict(re.findall(r'^([a-z_]+):[ \t]*(.*)$', frontmatter, re.M))
        for field in ('type', 'status', 'origin', 'valid_from', 'created', 'reviewed', 'sources'):
            with self.subTest(field=field):
                self.assertIn(field, fields, 'Шаблон должен проходить требования проверки знаний')
        if 'origin' in fields:
            self.assertIn(fields['origin'], ('stated', 'inferred', 'observation'))
        if 'valid_from' in fields:
            self.assertEqual(fields['valid_from'], 'null', 'Неизвестную дату нельзя придумывать')


if __name__ == '__main__':
    unittest.main()
