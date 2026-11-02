"""Фактический состав не должен терять новый тест или смешивать источники."""
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mutation_inventory', ROOT / 'scripts/mutation-inventory.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
CALENDAR_PYTHON = ROOT / 'modules/calendar/policy/.venv/bin/python'


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='inventory-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def unit(self, directory='tests', extra=''):
        return self.write(directory + '/test_example.py',
            'from pathlib import Path\nimport unittest\nclass Example(unittest.TestCase):\n'
            ' def test_first(self): Path("MUST_NOT_RUN").touch()\n' + extra)

    def test_new_method_is_missing_even_when_old_method_has_proof(self):
        first = dict(framework='unittest', source='tests/test_example.py', id='test_example.Example.test_first')
        second = dict(first, id='test_example.Example.test_second')
        missing, extra = inventory.coverage_gaps([first, second], [first])
        self.assertEqual(missing, [inventory.case_key(second)])
        self.assertEqual(extra, [])

    def test_same_id_in_another_source_cannot_replace_the_test(self):
        actual = dict(framework='unittest', source='tests/test_example.py', id='test_example.Example.test_first')
        foreign = dict(actual, source='modules/new/tests/test_example.py')
        missing, extra = inventory.coverage_gaps([actual], [foreign])
        self.assertEqual(missing, [inventory.case_key(actual)])
        self.assertEqual(extra, [inventory.case_key(foreign)])

    def test_empty_duplicate_and_noncanonical_records_are_rejected(self):
        first = dict(framework='unittest', source='tests/test_example.py', id='example')
        for records in ([], [first, first], [dict(first, source='tests/../test_example.py')]):
            with self.subTest(records=records), self.assertRaises(ValueError):
                inventory.coverage_gaps(records, [first])

    def test_discovery_keeps_sources_and_never_executes_test_bodies(self):
        self.unit()
        self.unit('modules/new/tests')
        records = inventory.collect(self.root)
        self.assertEqual({r['source'] for r in records},
                         {'tests/test_example.py', 'modules/new/tests/test_example.py'})
        self.assertEqual(len(records), 2)
        self.assertFalse((self.root / 'MUST_NOT_RUN').exists())

    def test_import_failure_and_uncollected_python_file_stop_inventory(self):
        for text in ('raise ImportError("broken fixture")\n', 'def test_plain(): pass\n'):
            self.write('tests/test_example.py', text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                inventory.collect(self.root)

    def test_source_alias_is_refused_without_reading_its_tests(self):
        target = self.write('outside.py', 'raise RuntimeError("must not import")\n')
        (self.root / 'tests').mkdir()
        (self.root / 'tests/test_example.py').symlink_to(target)
        with self.assertRaises(ValueError):
            inventory.source_record(self.root, 'unittest', 'example', self.root / 'tests/test_example.py')
        with self.assertRaises(ValueError):
            inventory.collect(self.root)

    def test_shell_ids_are_collected_without_running_scenarios(self):
        helper = self.root / 'tests/helpers/shell-scenarios.sh'
        helper.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'tests/helpers/shell-scenarios.sh', helper)
        self.write('tests/test-example.sh', '#!/bin/bash\nset -eu\n'
                   'source tests/helpers/shell-scenarios.sh\n'
                   'body() { touch MUST_NOT_RUN; }\n'
                   'scenario_declare first body\nscenario_declare second body\nscenario_main "$@"\n')
        records = inventory.collect(self.root)
        self.assertEqual(records, [dict(framework='shell', source='tests/test-example.sh', id='tests/test-example.sh::' + name)
                                   for name in ('first', 'second')])
        self.assertFalse((self.root / 'MUST_NOT_RUN').exists())

    @unittest.skipUnless(CALENDAR_PYTHON.exists(), 'нужно местное окружение календаря')
    def test_pytest_parameters_are_separate_without_running_them(self):
        self.write('modules/calendar/policy/tests/example_test.py',
                   'from pathlib import Path\nimport pytest\n'
                   '@pytest.mark.parametrize("number", [1, 2])\n'
                   'def test_number(number): Path("MUST_NOT_RUN").touch()\n')
        try:
            records = inventory.collect(self.root, Path(os.path.relpath(CALENDAR_PYTHON)))
        except ValueError:
            records = []
        self.assertEqual([r['id'] for r in records],
                         ['modules/calendar/policy/tests/example_test.py::test_number[1]',
                          'modules/calendar/policy/tests/example_test.py::test_number[2]'])
        self.assertFalse((self.root / 'MUST_NOT_RUN').exists())


if __name__ == '__main__':
    unittest.main()
