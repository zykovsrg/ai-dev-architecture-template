"""Behavioural fixtures for the isolated framework event adapter."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / 'scripts/test-method-capture.py'
PYTEST_PYTHON = ROOT / 'modules/calendar/policy/.venv/bin/python'


class CaptureTests(unittest.TestCase):
    def capture(self, source, framework='unittest', extra=None, files=None, helpers=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'test_fixture.py').write_text(source)
            for name, content in (files or {}).items():
                (root / name).write_text(content)
            output = root / 'events.json'
            python = str(PYTEST_PYTHON) if framework == 'pytest' else sys.executable
            args = extra if extra is not None else (['test_fixture'] if framework == 'unittest' else ['test_fixture.py', '-q'])
            helper_args = [part for name in (helpers or []) for part in ('--allow-helper', str(root / name))]
            process = subprocess.run([python, str(ADAPTER), '--framework', framework,
                                      '--output', str(output)] + helper_args + ['--'] + args,
                                     cwd=root, capture_output=True, text=True)
            self.assertTrue(output.exists(), process.stderr)
            return process, json.loads(output.read_text())

    def test_unittest_records_outer_ids_and_subtests_only(self):
        _, data = self.capture('''import unittest
class Fixture(unittest.TestCase):
 def test_outer(self):
  class Inner(unittest.TestCase):
   def test_hidden(self): pass
  unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(Inner))
  for value in (1, 2):
   with self.subTest(value=value): self.assertGreater(value, 0)
 def test_skip(self): self.skipTest('reason')
 @unittest.skip('decorator')
 def test_skip_decorated(self): pass
''')
        self.assertEqual(data['collected_ids'], ['test_fixture.Fixture.test_outer', 'test_fixture.Fixture.test_skip', 'test_fixture.Fixture.test_skip_decorated'])
        self.assertEqual(len([r for r in data['results'] if r['kind'] == 'subtest']), 2)
        self.assertEqual([r['status'] for r in data['results'] if r['kind'] == 'test'], ['passed', 'skipped', 'skipped'])
        self.assertTrue(all(Path(r['source_path']).name == 'test_fixture.py' for r in data['results']))
        self.assertTrue(data['complete'])

    def test_unittest_own_assertion_excludes_foreign_errors_and_setup(self):
        _, data = self.capture('''import unittest
from foreign import fail
class Fixture(unittest.TestCase):
 def test_own(self): self.assertEqual(1, 2)
 def test_foreign(self): fail()
 def test_error(self): raise ValueError('FAILED')
class Setup(unittest.TestCase):
 def setUp(self): self.assertEqual(1, 2)
 def test_never(self): pass
''', files={'foreign.py': "def fail():\n assert False, 'foreign'\n"})
        own = [r for r in data['results'] if r.get('own_assertion')]
        self.assertEqual([r['id'] for r in own], ['test_fixture.Fixture.test_own'])
        self.assertEqual(own[0]['exception']['type'], 'builtins.AssertionError')
        self.assertEqual(Path(own[0]['exception']['location']['path']).name, 'test_fixture.py')
        self.assertEqual(data['exit_code'], 1)

    def test_unittest_empty_and_import_failure_are_incomplete(self):
        _, empty = self.capture('')
        _, broken = self.capture("raise ImportError('broken')\n")
        self.assertFalse(empty['complete'])
        self.assertFalse(broken['complete'])
        self.assertFalse(any(r.get('own_assertion') for r in broken['results']))

    @unittest.skipUnless(PYTEST_PYTHON.exists(), 'local pytest environment unavailable')
    def test_pytest_parameter_ids_and_phases(self):
        _, data = self.capture('''import pytest
@pytest.mark.parametrize('value', [1, 2])
def test_parameter(value): assert value > 0
@pytest.mark.skip(reason='reason')
def test_skip(): pass
''', 'pytest')
        self.assertEqual(data['collected_ids'], ['test_fixture.py::test_parameter[1]', 'test_fixture.py::test_parameter[2]', 'test_fixture.py::test_skip'])
        self.assertEqual([r['phase'] for r in data['results'] if r['id'].endswith('[1]')], ['setup', 'call', 'teardown'])
        self.assertEqual(len([r for r in data['results'] if r['phase'] == 'call' and r['status'] == 'passed']), 2)
        self.assertTrue(any(r['status'] == 'skipped' for r in data['results']))

    @unittest.skipUnless(PYTEST_PYTHON.exists(), 'local pytest environment unavailable')
    def test_pytest_assertions_exclude_foreign_and_non_call_errors(self):
        _, data = self.capture('''import pytest
from foreign import fail
@pytest.fixture
def setup_error(): assert False, 'setup'
@pytest.fixture
def teardown_error():
 yield
 assert False, 'teardown'
def test_setup(setup_error): pass
def test_teardown(teardown_error): pass
def test_own(): assert 1 == 2
def test_explicit(): pytest.fail('own')
def test_foreign(): fail()
def test_error(): raise ValueError('FAILED')
''', 'pytest', files={'foreign.py': "def fail():\n assert False, 'foreign'\n"})
        own = [r['id'] for r in data['results'] if r.get('own_assertion')]
        self.assertEqual(own, ['test_fixture.py::test_own', 'test_fixture.py::test_explicit'])
        self.assertTrue(any(r['phase'] == 'teardown' and r['status'] == 'error' for r in data['results']))

    @unittest.skipUnless(PYTEST_PYTHON.exists(), 'local pytest environment unavailable')
    def test_pytest_empty_and_collection_error_are_incomplete(self):
        _, empty = self.capture('', 'pytest')
        _, broken = self.capture("raise ImportError('broken')\n", 'pytest')
        self.assertFalse(empty['complete'])
        self.assertFalse(broken['complete'])
        self.assertFalse(any(r.get('own_assertion') for r in broken['results']))


    def test_unittest_assertion_origin_rejects_bare_raise(self):
        _, data = self.capture("""import unittest
from helper import check, bare
class Fixture(unittest.TestCase):
 def test_bare(self): raise AssertionError('bare')
 def test_same_line(self): assert True; raise AssertionError('bare')
 def test_helper_bare(self): bare()
 def test_helper(self): check()
 def test_multiline(self):
  assert (
   1 == 2
  ), 'multiline'
 def test_context(self):
  with self.assertRaises(ValueError): pass
class AsyncFixture(unittest.IsolatedAsyncioTestCase):
 async def test_async(self): self.assertEqual(1, 2)
""", files={'helper.py': "def check():\n assert 1 == 2\ndef bare():\n raise AssertionError('bare helper')\n"}, helpers=['helper.py'])
        own = {r['id']: (r['exception'].get('assertion_origin') or {}).get('kind')
               for r in data['results'] if r.get('own_assertion')}
        self.assertEqual(own, {
            'test_fixture.AsyncFixture.test_async': 'unittest_assertion',
            'test_fixture.Fixture.test_context': 'unittest_assertion',
            'test_fixture.Fixture.test_helper': 'python_assert',
            'test_fixture.Fixture.test_multiline': 'python_assert'})
        multiline = next(r for r in data['results'] if r['id'].endswith('test_multiline'))
        self.assertIn('1 == 2', multiline['exception']['assertion_origin']['source'])

    @unittest.skipUnless(PYTEST_PYTHON.exists(), 'local pytest environment unavailable')
    def test_pytest_assertion_origin_rejects_bare_raise(self):
        _, data = self.capture("""import pytest
from helper import check, bare, explicit
def test_bare(): raise AssertionError('bare')
def test_same_line(): assert True; raise AssertionError('bare')
def test_failed_type(): raise pytest.fail.Exception('bare failed')
def test_helper_bare(): bare()
def test_helper(): check()
def test_explicit_helper(): explicit()
def test_multiline():
 assert (
  1 == 2
 ), 'multiline'
""", 'pytest', files={'helper.py': "import pytest\ndef check():\n assert 1 == 2\ndef bare():\n raise AssertionError('bare helper')\ndef explicit():\n pytest.fail('actual failure')\n"}, helpers=['helper.py'])
        own = {r['id']: (r['exception'].get('assertion_origin') or {}).get('kind')
               for r in data['results'] if r.get('own_assertion')}
        self.assertEqual(own, {
            'test_fixture.py::test_helper': 'python_assert',
            'test_fixture.py::test_explicit_helper': 'pytest_fail',
            'test_fixture.py::test_multiline': 'python_assert'})

    @unittest.skipUnless(PYTEST_PYTHON.exists(), 'local pytest environment unavailable')
    def test_pytest_testcase_assertion_uses_the_test_location(self):
        _, data = self.capture('import unittest\nfrom product import allowed\nclass Fixture(unittest.TestCase):\n def test_zero(self): self.assertFalse(allowed(0))\n', 'pytest', files={'product.py': 'def allowed(value): return value >= 0\n'})
        own = [r for r in data['results'] if r.get('own_assertion')]
        self.assertEqual([r['id'] for r in own], ['test_fixture.py::Fixture::test_zero'])
        self.assertEqual(own[0]['exception']['assertion_origin']['kind'], 'unittest_assertion')
        self.assertEqual(Path(own[0]['exception']['location']['path']).name, 'test_fixture.py')

    @unittest.skipUnless(PYTEST_PYTHON.exists(), 'local pytest environment unavailable')
    def test_pytest_testcase_fixture_assertion_is_not_own(self):
        for fixture in ['setUp', 'tearDown', 'addCleanup']:
            with self.subTest(fixture=fixture):
                source = ('import unittest\nclass Fixture(unittest.TestCase):\n'
                          ' def ' + fixture + '(self): self.assertEqual(1, 2)\n'
                          ' def test_body(self): pass\n')
                if fixture == 'addCleanup':
                    source = ('import unittest\nclass Fixture(unittest.TestCase):\n'
                              ' def setUp(self): self.addCleanup(self.clean)\n'
                              ' def clean(self): self.assertEqual(1, 2)\n'
                              ' def test_body(self): pass\n')
                _, data = self.capture(source, 'pytest')
                self.assertTrue(any(r['status'] == 'failed' for r in data['results']), data)
                self.assertFalse(any(r.get('own_assertion') for r in data['results']), data)

    @unittest.skipUnless(PYTEST_PYTHON.exists(), 'local pytest environment unavailable')
    def test_pytest_raises_match_failure_is_own_only_in_the_test(self):
        _, data = self.capture("""import pytest
from foreign import mismatch
@pytest.fixture
def fixture_mismatch():
 with pytest.raises(ValueError, match='expected'):
  raise ValueError('different')
def test_fixture(fixture_mismatch): pass
def test_match():
 with pytest.raises(ValueError, match='expected'):
  raise ValueError('different')
def test_wrong_type():
 with pytest.raises(ValueError, match='expected'):
  raise TypeError('different')
def test_foreign(): mismatch()
def test_context_without_enter():
 context = pytest.raises(ValueError, match='expected')
 context.excinfo = None
 context.__exit__(ValueError, ValueError('different'), None)
""", 'pytest', files={'foreign.py': "import pytest\ndef mismatch():\n with pytest.raises(ValueError, match='expected'):\n  raise ValueError('different')\n"})
        own = [r for r in data['results'] if r.get('own_assertion')]
        self.assertEqual([r['id'] for r in own], ['test_fixture.py::test_match'])
        self.assertEqual(own[0]['exception']['assertion_origin']['kind'], 'pytest_fail')
        self.assertEqual(own[0]['exception']['assertion_origin']['assertion_api'], 'pytest.raises')
        self.assertEqual(own[0]['exception']['location']['function'], 'test_match')

    def test_unittest_shared_fixture_events_preserve_remaining_tests(self):
        for fixture, error_type in [('setUpClass', 'builtins.ValueError'),
                                    ('tearDownClass', 'builtins.ValueError')]:
            source = ("import unittest\nclass Bad(unittest.TestCase):\n @classmethod\n def " + fixture +
                      "(cls): raise ValueError('fixture error')\n def test_bad(self): pass\n" +
                      "class Good(unittest.TestCase):\n def test_good(self): pass\n")
            _, data = self.capture(source)
            self.assertEqual(data['infrastructure_errors'], [])
            self.assertEqual(data['exit_code'], 1)
            self.assertTrue(data['complete'])
            self.assertTrue(any(r['id'] == 'test_fixture.Good.test_good' and r['status'] == 'passed'
                                for r in data['results']))
            fixtures = [r for r in data['results'] if r['kind'] == 'fixture']
            self.assertEqual(len(fixtures), 1)
            self.assertEqual(fixtures[0]['phase'], 'fixture')
            self.assertEqual(fixtures[0]['exception']['type'], error_type)
            self.assertFalse(fixtures[0]['own_assertion'])


if __name__ == '__main__':
    unittest.main()
