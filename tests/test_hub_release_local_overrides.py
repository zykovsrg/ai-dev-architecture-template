import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.hub_release import apply, build_manifest, preview, release_sources

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'modules/calendar/rules.md'
TARGET = 'ai/rules/calendar.md'


class LocalOverrideTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.hub = self.root / 'hub'
        self.hub.mkdir()
        self.source = self.root / 'source'
        for relative in release_sources(ROOT):
            destination = self.source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
        generic = hashlib.sha256((self.source / SOURCE).read_bytes()).hexdigest()
        (self.source / SOURCE).write_text('personal calendar policy\n')
        local = hashlib.sha256((self.source / SOURCE).read_bytes()).hexdigest()
        self.marker = {'source_sha256': {SOURCE: generic}, 'scope': 'local-hub-only',
                       'hub': str(self.hub), 'permissions_expanded': False,
                       'local_overrides': {SOURCE: {'installed_target': TARGET,
                           'installed_sha256': local, 'generic_source_sha256': generic,
                           'reason': 'Preserve personal policy'}}}
        self.write_marker()

    def write_marker(self):
        (self.source / 'LOCAL-RELEASE.json').write_text(json.dumps(self.marker))

    def install(self):
        plan = preview(self.source, self.hub)
        apply(self.source, self.hub, plan['plan_sha256'])

    def row(self, plan):
        return next(row for row in plan['operations'] if row['target'] == TARGET)

    def test_build_carries_verified_override_provenance(self):
        manifest = build_manifest(self.source)
        self.assertEqual(manifest['hub'], str(self.hub))
        self.assertEqual(manifest['scope'], 'local-hub-only')
        self.assertEqual(manifest['local_overrides'][TARGET],
                         dict(self.marker['local_overrides'][SOURCE], source=SOURCE))

    def test_invalid_package_metadata_is_rejected(self):
        original = json.loads(json.dumps(self.marker))
        cases = ['hash', 'provenance', 'traversal', 'target', 'scope', 'hub', 'schema', 'size']
        for case in cases:
            with self.subTest(case=case):
                self.marker = json.loads(json.dumps(original))
                override = self.marker['local_overrides'][SOURCE]
                if case == 'hash': override['installed_sha256'] = '0' * 64
                if case == 'provenance': override['generic_source_sha256'] = '0' * 64
                if case == 'traversal': self.marker['local_overrides']['../rules.md'] = self.marker['local_overrides'].pop(SOURCE)
                if case == 'target': override['installed_target'] = 'ai/rules/tasks.md'
                if case == 'scope': self.marker['scope'] = 'every-hub'
                if case == 'hub': self.marker['hub'] = 'relative/hub'
                if case == 'schema': self.marker['local_overrides'] = []
                if case == 'size': override['reason'] = 'x' * 1048576
                self.write_marker()
                with self.assertRaises(ValueError):
                    build_manifest(self.source)

    def test_symlink_metadata_is_rejected(self):
        marker = self.source / 'LOCAL-RELEASE.json'
        marker.rename(self.source / 'marker.json')
        marker.symlink_to(self.source / 'marker.json')
        with self.assertRaises(ValueError):
            build_manifest(self.source)

    def test_package_cannot_target_foreign_hub(self):
        other = self.root / 'other'
        other.mkdir()
        with self.assertRaises(ValueError):
            preview(self.source, other)

    def test_unchanged_generic_source_keeps_local_override(self):
        self.install()
        before = (self.hub / TARGET).read_bytes()
        plan = preview(ROOT, self.hub)
        self.assertEqual(self.row(plan)['action'], 'keep')
        apply(ROOT, self.hub, plan['plan_sha256'])
        self.assertEqual((self.hub / TARGET).read_bytes(), before)
        installed = json.loads((self.hub / '.local/hub-release/installed.json').read_text())
        self.assertIn(TARGET, installed['local_overrides'])

    def test_edited_local_override_stays_conflict_for_unchanged_generic(self):
        self.install()
        (self.hub / TARGET).write_text('fresh personal change\n')
        self.assertEqual(self.row(preview(ROOT, self.hub))['action'], 'conflict')

    def test_generic_update_cannot_replace_local_override(self):
        self.install()
        changed = self.root / 'changed-generic'
        shutil.copytree(ROOT, changed, ignore=shutil.ignore_patterns(
            'experiments', 'docs', 'obsidian-vault', 'tmp', '.venv', '__pycache__', '.git'))
        (changed / SOURCE).write_text((ROOT / SOURCE).read_text() + '\nnew generic rule\n')
        plan = preview(changed, self.hub)
        self.assertEqual(self.row(plan)['action'], 'conflict')
        before = (self.hub / TARGET).read_bytes()
        with self.assertRaises(ValueError):
            apply(ROOT, self.hub, plan['plan_sha256'])
        self.assertEqual((self.hub / TARGET).read_bytes(), before)

    def test_generic_update_preserves_marker_when_local_bytes_match(self):
        self.install()
        (self.source / 'LOCAL-RELEASE.json').unlink()
        changed = self.source / 'modules/core/data/AGENTS.md'
        changed.write_text(changed.read_text() + '\nunrelated update\n')
        plan = preview(self.source, self.hub)
        self.assertEqual(self.row(plan)['action'], 'keep')
        apply(self.source, self.hub, plan['plan_sha256'])
        installed = json.loads((self.hub / '.local/hub-release/installed.json').read_text())
        self.assertIn(TARGET, installed['local_overrides'])
        self.assertEqual(installed['hub'], str(self.hub))
        self.assertEqual(self.row(preview(ROOT, self.hub))['action'], 'keep')

    def test_fresh_local_edits_stay_conflicts(self):
        self.install()
        (self.hub / TARGET).write_text('fresh personal change\n')
        self.assertEqual(self.row(preview(self.source, self.hub))['action'], 'conflict')

    def test_replacement_package_cannot_change_existing_pin_or_scope(self):
        self.install()
        original = (self.source / SOURCE).read_bytes()
        installed = self.hub / '.local/hub-release/installed.json'
        before = installed.read_bytes()
        for change in ('pin', 'scope'):
            with self.subTest(change=change):
                (self.source / SOURCE).write_bytes(original)
                self.marker['scope'] = 'local-hub-only'
                if change == 'pin':
                    (self.source / SOURCE).write_text('replacement personal policy\n')
                    self.marker['local_overrides'][SOURCE]['installed_sha256'] = hashlib.sha256(
                        (self.source / SOURCE).read_bytes()).hexdigest()
                else:
                    self.marker['local_overrides'][SOURCE]['installed_sha256'] = hashlib.sha256(original).hexdigest()
                    self.marker['scope'] = 'every-hub'
                self.write_marker()
                with self.assertRaises(ValueError):
                    preview(self.source, self.hub)
                self.assertEqual(installed.read_bytes(), before)
                self.assertEqual((self.hub / TARGET).read_bytes(), original)

    def test_module_removal_cannot_erase_override(self):
        self.install()
        plan = preview(self.source, self.hub, without=['calendar', 'planning'])
        self.assertEqual(self.row(plan)['action'], 'conflict')
        with self.assertRaises(ValueError):
            apply(self.source, self.hub, plan['plan_sha256'], without=['calendar', 'planning'])
        self.assertTrue((self.hub / TARGET).exists())
