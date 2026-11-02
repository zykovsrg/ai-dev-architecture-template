"""Синтетические проверки повторного чтения иерархии; без вызовов приложения."""
import copy
import unittest
import uuid
from test_reminders_project_list_extras import DetailFake, LID, AID
import test_reminders_project_list_migration as base


class HierarchyFake(DetailFake):
    def __init__(self):
        super().__init__()
        self.rows = []
        for i in range(40):
            parent = str(uuid.UUID(int=i * 3 + 1))
            for child_index, title in [(1, 'Zulu'), (2, 'Alpha')]:
                self.rows.append(dict(id=str(uuid.UUID(int=i * 3 + child_index + 1)),
                    list_id=LID, list='Работа', title=title, version='1', parent_id=parent))
            self.rows.append(dict(id=parent, list_id=LID, list='Работа', title='Parent', version='1',
                notes='Полные поля', alarms=['2026-10-27'],
                subtasks=[dict(id=self.rows[-2]['id'], title='Zulu'), dict(id=self.rows[-1]['id'], title='Alpha')]))

    def call(self, tool, args):
        result = super().call(tool, args)
        if tool == 'find_reminders' and not args.get('detail'):
            result['reminders'].sort(key=lambda row: row['title'])
        return result


class ParentReadTests(unittest.TestCase):
    def setUp(self):
        self.m = base.module()
        self.native = HierarchyFake()
        self.m.metadata(self.native)
        self.m.rows(self.native, LID)
        self.native.calls.clear()

    def test_many_parents_preserve_native_full_snapshot_with_bounded_reads(self):
        expected = {row['id']: copy.deepcopy(row) for row in self.native.rows}
        self.assertEqual(self.m.rows(self.native, LID), expected)
        self.assertEqual(sum(tool == 'get_reminder' for tool, _ in self.native.calls), 0)
        self.assertLessEqual(len(self.native.calls), 2)

    def test_same_version_child_edits_moves_and_empty_parent_use_bounded_reads(self):
        first, second = self.native.rows[2], self.native.rows[5]
        moved = self.native.rows[0]
        moved.update(title='Изменено', completed=True, parent_id=second['id'])
        self.native.rows[1].pop('parent_id')
        first.pop('subtasks')
        second['subtasks'].append(dict(id=moved['id'], title='Изменено', completed=True))
        expected = {row['id']: copy.deepcopy(row) for row in self.native.rows}
        self.assertEqual(self.m.rows(self.native, LID), expected)
        self.assertEqual(sum(tool == 'get_reminder' for tool, _ in self.native.calls), 0)
        self.assertLessEqual(len(self.native.calls), 2)

    def test_hierarchy_refresh_rejects_malformed_full_snapshot_before_cache_commit(self):
        before = copy.deepcopy(self.native._migration_detail_cache)
        for bad in ['unknown', 'version', 'parent', 'type', 'duplicate', 'partial']:
            with self.subTest(bad=bad):
                original = copy.deepcopy(self.native.rows)
                if bad == 'unknown': self.native.rows[2]['foreign_field'] = True
                elif bad == 'version': self.native.rows[2]['version'] = 2
                elif bad == 'parent': self.native.rows[0]['parent_id'] = AID
                elif bad == 'type': self.native.rows[0]['completed'] = 1
                elif bad == 'duplicate': self.native.rows.append(copy.deepcopy(self.native.rows[0]))
                else: self.native.bad = dict(count=500, more=1)
                with self.assertRaises(ValueError): self.m.rows(self.native, LID)
                self.assertEqual(self.native._migration_detail_cache, before)
                self.native.rows = original
                self.native.bad = None

    def test_same_version_reordering_is_observed_even_when_summary_is_identical(self):
        self.native.rows[2]['subtasks'].reverse()
        result = self.m.rows(self.native, LID)
        self.assertEqual(result[self.native.rows[2]['id']]['subtasks'], self.native.rows[2]['subtasks'])
        self.assertEqual(sum(tool == 'get_reminder' for tool, _ in self.native.calls), 0)

    def test_legacy_hierarchy_keeps_individual_parent_read(self):
        self.native.support = False
        self.m.metadata(self.native)
        self.m.rows(self.native, LID)
        self.assertTrue(any(tool == 'get_reminder' for tool, _ in self.native.calls))
        self.assertFalse(any(args.get('detail') for tool, args in self.native.calls if tool == 'find_reminders'))

    def test_new_hierarchy_after_flat_cache_reads_exact_native_order(self):
        native = DetailFake()
        self.m.metadata(native)
        self.m.rows(native, LID)
        native.calls.clear()
        child = copy.deepcopy(self.native.rows[0])
        child['parent_id'] = AID
        native.rows.append(child)
        native.rows[0]['subtasks'] = [dict(id=child['id'], title=child['title'])]
        self.assertEqual(self.m.rows(native, LID), {row['id']: row for row in native.rows})
        self.assertEqual(sum(tool == 'get_reminder' for tool, _ in native.calls), 0)
        self.assertEqual(len(native.calls), 2)
