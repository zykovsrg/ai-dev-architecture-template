"""Повторная загрузка кода не переиспользует модули и не скрывает изменение файла."""
import builtins
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/reminders_reads.py'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CodeCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.scripts = self.root / 'scripts'
        self.scripts.mkdir()
        copy = self.scripts / 'reminders_reads.py'
        shutil.copy2(SOURCE, copy)
        self.reads = load(copy, 'scoped_reads_subject')
        self.sample = self.scripts / 'sample.py'
        self.sample.write_text('STATE = []\ndef value():\n return 1\n')

    def test_reuses_code_but_keeps_module_globals_independent(self):
        with self.reads.run_scope():
            first = load(self.sample, 'first')
            second = load(self.sample, 'second')
        self.assertIs(first.value.__code__, second.value.__code__)
        self.assertIsNot(first, second)
        first.STATE.append('changed')
        self.assertEqual(second.STATE, [])

    def test_exact_bytes_invalidate_same_size_and_timestamp_and_deleted_source(self):
        stat = self.sample.stat()
        with self.reads.run_scope():
            first = load(self.sample, 'first')
            self.sample.write_text(self.sample.read_text().replace('return 1', 'return 2'))
            os.utime(self.sample, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            second = load(self.sample, 'second')
            self.assertEqual(second.value(), 2)
            self.assertIsNot(first.value.__code__, second.value.__code__)
            self.sample.unlink()
            with self.assertRaises(FileNotFoundError):
                load(self.sample, 'missing')

    def test_external_and_symlink_loaders_unchanged_and_hook_restored_after_exception(self):
        outside = self.root / 'outside.py'
        outside.write_text('value = 7\n')
        symlink = self.scripts / 'linked.py'
        symlink.symlink_to(outside)
        loader = importlib.machinery.SourceFileLoader
        previous = loader.get_code
        seen = []
        def tracked(subject, fullname):
            seen.append(subject.path)
            return previous(subject, fullname)
        with patch.object(loader, 'get_code', tracked):
            with self.assertRaisesRegex(RuntimeError, 'scope failure'):
                with self.reads.run_scope():
                    self.assertIsNot(loader.get_code, tracked)
                    self.assertEqual(load(outside, 'outside').value, 7)
                    self.assertEqual(load(symlink, 'linked').value, 7)
                    raise RuntimeError('scope failure')
            self.assertIs(loader.get_code, tracked)
        self.assertIn(str(outside), seen)
        self.assertIn(str(symlink), seen)
        self.assertIs(loader.get_code, previous)

    def test_nested_scope_shares_code_and_next_scope_starts_fresh(self):
        compiled = []
        original = builtins.compile
        def counted(source, filename, *args, **kwargs):
            if str(filename) == str(self.sample):
                compiled.append(filename)
            return original(source, filename, *args, **kwargs)
        with patch.object(builtins, 'compile', counted):
            with self.reads.run_scope():
                first = load(self.sample, 'first')
                with self.reads.run_scope():
                    second = load(self.sample, 'second')
                third = load(self.sample, 'third')
                self.assertIs(first.value.__code__, second.value.__code__)
                self.assertIs(second.value.__code__, third.value.__code__)
            with self.reads.run_scope():
                fourth = load(self.sample, 'fourth')
            self.assertIsNot(first.value.__code__, fourth.value.__code__)
        self.assertEqual(len(compiled), 2)


if __name__ == '__main__':
    unittest.main()
