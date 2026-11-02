"""Защитные отказы обновления: состояние до отказа должно сохраниться."""
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest import mock
from scripts.hub_release import apply, preview, release_sources

ROOT = Path(__file__).resolve().parents[1]


def source_copy(root):
    source = root / 'source'
    for relative in release_sources(ROOT):
        origin = ROOT / relative
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, target)
    return source


class ReleaseSafetyTests(unittest.TestCase):
    def test_revision_mismatch_refuses_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / 'hub'
            hub.mkdir()
            plan = preview(ROOT, hub, source_sha='a' * 40)
            with self.assertRaisesRegex(ValueError, 'source revision changed'):
                apply(ROOT, hub, plan['plan_sha256'], source_sha='a' * 40,
                      confirmed_source_sha='b' * 40)
            self.assertEqual(list(hub.iterdir()), [])

    def test_changed_source_invalidates_reviewed_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = source_copy(root)
            hub = root / 'hub'
            hub.mkdir()
            plan = preview(source, hub)
            entry = source / 'modules/core/data/AGENTS.md'
            entry.write_text(entry.read_text() + '\nИзменение после просмотра.\n')
            with self.assertRaisesRegex(ValueError, 'plan changed'):
                apply(source, hub, plan['plan_sha256'])
            self.assertEqual(list(hub.iterdir()), [])

    def test_local_change_blocks_apply_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            hub = Path(directory) / 'hub'
            hub.mkdir()
            plan = preview(ROOT, hub)
            apply(ROOT, hub, plan['plan_sha256'])
            entry = hub / 'AGENTS.md'
            entry.write_bytes(b'local changes\n')
            plan = preview(ROOT, hub)
            with self.assertRaisesRegex(ValueError, 'conflicting local changes'):
                apply(ROOT, hub, plan['plan_sha256'])
            self.assertEqual(entry.read_bytes(), b'local changes\n')

    def test_release_metadata_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            state = root / 'hub/.local/hub-release'
            state.mkdir(parents=True)
            other = root / 'other.json'
            other.write_text('{"files": []}')
            (state / 'installed.json').symlink_to(other)
            with self.assertRaisesRegex(ValueError, 'unsafe installed release metadata'):
                preview(ROOT, root / 'hub')
            self.assertEqual(other.read_text(), '{"files": []}')

    def test_metadata_failure_restores_previous_bytes_and_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = source_copy(root)
            hub = root / 'hub'
            hub.mkdir()
            plan = preview(source, hub)
            apply(source, hub, plan['plan_sha256'])
            entry = hub / 'AGENTS.md'
            entry.chmod(0o640)
            original = entry.read_bytes()
            metadata = hub / '.local/hub-release/installed.json'
            original_metadata = metadata.read_bytes()
            changed = source / 'modules/core/data/AGENTS.md'
            changed.write_text(changed.read_text() + '\nОбновлённая инструкция.\n')
            plan = preview(source, hub)
            import os
            original_replace = os.replace

            def fail_metadata(source_path, target):
                if Path(target) == metadata:
                    raise OSError('controlled metadata failure')
                return original_replace(source_path, target)

            with mock.patch('scripts.hub_release.os.replace', side_effect=fail_metadata):
                with self.assertRaisesRegex(OSError, 'controlled metadata failure'):
                    apply(source, hub, plan['plan_sha256'])
            self.assertEqual(entry.read_bytes(), original)
            self.assertEqual(stat.S_IMODE(entry.stat().st_mode), 0o640)
            self.assertEqual(metadata.read_bytes(), original_metadata)
