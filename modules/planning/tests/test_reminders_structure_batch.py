"""Полный снимок структуры: пакетное чтение с прежними гарантиями."""
import copy
import importlib.util
import os
from pathlib import Path
import unittest

SOURCE = Path(os.environ.get('STRUCTURE_BATCH_SOURCE', Path(__file__).resolve().parents[1] / 'scripts/reminders_structure.py'))
spec = importlib.util.spec_from_file_location('batch_structure', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
L1, L2 = '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002'
P, C, X = '00000000-0000-0000-0000-000000000011', '00000000-0000-0000-0000-000000000012', '00000000-0000-0000-0000-000000000013'

class Native:
    def __init__(self, capability=True):
        self.capability = capability
        self.calls = []
        self.change = lambda value: value
        self.details = {
            L1: [dict(id=P, list_id=L1, list='Первый', title='Родитель', version='v1', notes='Текст',
                      subtasks=[dict(id=C, title='Ребёнок', completed=False)]),
                 dict(id=C, list_id=L1, list='Первый', title='Ребёнок', version='v2', parent_id=P)],
            L2: [dict(id=X, list_id=L2, list='Второй', title='Задача', version='v3')],
        }
        self.summaries = self.project()
    def project(self):
        result = copy.deepcopy(self.details)
        for rows in result.values():
            for row in rows:
                for key in ('list_id', 'subtasks', 'alarms', 'early_alerts', 'urls', 'smart_lists', 'shared_list'):
                    row.pop(key, None)
                if isinstance(row.get('images'), list): row['images'] = len(row['images'])
        return result
    def call(self, tool, args):
        self.calls.append((tool, copy.deepcopy(args)))
        if tool == 'list_lists':
            return dict(lists=[dict(id=L1, name='Первый', group_id='g'), dict(id=L2, name='Второй', group_id='g')],
                        groups=[dict(id='g', name='Группа')], detailed_reminder_snapshot=self.capability)
        if tool == 'find_reminders':
            lid = args['list']
            if args.get('detail'):
                return self.change(dict(detail=True, count=len(self.details[lid]), reminders=copy.deepcopy(self.details[lid])))
            return dict(count=len(self.summaries[lid]), reminders=copy.deepcopy(self.summaries[lid]))
        if tool == 'get_reminder':
            return copy.deepcopy(next(row for rows in self.details.values() for row in rows if row['id'] == args['id']))
        raise AssertionError(tool)

def snapshot(native, **kwargs):
    return m.snapshot(native, {L1: {}, L2: {}}, {'Первый', 'Второй'}, **kwargs)

class BatchSnapshotTests(unittest.TestCase):
    def test_batch_preserves_exact_legacy_snapshot_and_reduces_calls(self):
        old, new = Native(False), Native()
        self.assertEqual(snapshot(old, detailed=True), snapshot(new, detailed=True))
        self.assertEqual(sum(tool == 'get_reminder' for tool, _ in new.calls), 0)
        self.assertEqual(sum(bool(args.get('detail')) for _, args in new.calls), 2)
    def test_absent_capability_keeps_legacy_detail_reads(self):
        native = Native(False)
        snapshot(native, detailed=True)
        self.assertEqual(sum(tool == 'get_reminder' for tool, _ in native.calls), 3)
        self.assertFalse(any(args.get('detail') for _, args in native.calls))
    def test_shallow_snapshot_keeps_narrow_detail_read(self):
        native = Native()
        value = snapshot(native, detailed_ids={P})
        self.assertEqual([args['id'] for tool, args in native.calls if tool == 'get_reminder'], [P])
        self.assertFalse(any(args.get('detail') for _, args in native.calls))
        self.assertIn('subtasks', value['reminders'][P])
        self.assertNotIn('subtasks', value['reminders'][C])
    def test_summary_projection_drift_is_rejected(self):
        for field, value in [('version', 'new'), ('title', 'Изменено'), ('notes', 'Новый текст'), ('due', '2026-11-02')]:
            with self.subTest(field=field):
                native = Native()
                native.summaries[L1][0][field] = value
                with self.assertRaisesRegex(ValueError, 'structure_snapshot_changed'):
                    snapshot(native, detailed=True)
    def test_extra_detail_row_is_rejected(self):
        native = Native()
        native.summaries[L2] = []
        with self.assertRaisesRegex(ValueError, 'structure_snapshot_changed'):
            snapshot(native, detailed=True)
    def test_invalid_batch_protocol_is_not_silently_downgraded(self):
        native = Native()
        native.change = lambda value: dict(value, detail=False)
        with self.assertRaisesRegex(ValueError, 'incomplete_detailed_snapshot'):
            snapshot(native, detailed=True)
        self.assertFalse(any(tool == 'get_reminder' for tool, _ in native.calls))
    def test_cyclic_batch_hierarchy_is_rejected(self):
        native = Native()
        native.details[L1][0]['parent_id'] = C
        native.details[L1][1]['subtasks'] = [dict(id=P, title='Родитель', completed=False)]
        native.summaries = native.project()
        with self.assertRaisesRegex(ValueError, 'invalid_detailed_parent_reference'):
            snapshot(native, detailed=True)
    def test_each_snapshot_reads_fresh_details_and_child_order(self):
        native = Native()
        native.details[L1].append(dict(id=X, list_id=L1, list='Первый', title='Ещё ребёнок', version='v3', parent_id=P))
        native.details[L2] = []
        native.details[L1][0]['subtasks'].append(dict(id=X, title='Ещё ребёнок', completed=False))
        native.summaries = native.project()
        first = snapshot(native, detailed=True)
        native.details[L1][0]['subtasks'].reverse()
        second = snapshot(native, detailed=True)
        self.assertNotEqual(first, second)
        self.assertEqual(sum(bool(args.get('detail')) for _, args in native.calls), 4)

if __name__ == '__main__':
    unittest.main()
