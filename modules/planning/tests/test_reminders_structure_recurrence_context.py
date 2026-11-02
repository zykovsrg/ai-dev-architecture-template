"""Полный reconcile=True с действующей структурой и настоящей квитанцией исчезновения."""
import copy
import json
import unittest
from unittest.mock import patch
import test_reminders_engine as fixture


class FullStructureRecurrenceTests(unittest.TestCase):
    def test_full_structure_noop_with_absence_receipt_uses_one_capture(self):
        helper = fixture.IntegrationTests('runTest')
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        f, m, e, c = helper.f, helper.m, helper.e, helper.core
        f.native.rows.pop(c.PID)
        f.native.rows[c.RID].pop('parent_id')
        f.native.rows[c.RID]['repeat'] = {'frequency': 'daily'}
        binding = f.config['projects']['demo']
        binding.update(layout='project_list', parent_id=None,
                       history={'00000000-0000-0000-0000-000000000099':
                                dict(original_id=c.RID, task_id=c.TID, project_id='demo')})
        (f.hub / 'ai/project-cards').mkdir()
        (f.hub / 'ai/project-cards/demo.md').write_text('Project ID: demo\nStatus: active\nprimary_archiproject: a\n')
        registry = f.hub / 'ai/project-registry.md'
        registry.write_text(registry.read_text() + 'Card: ai/project-cards/demo.md\n')
        (f.hub / 'ai/archiprojects.md').write_text('## a\n```yaml\nid: a\nname: a\nstatus: active\nkind: group\n```\n')
        groups, pins = f.hub / 'ai/groups.json', f.hub / 'ai/pins.json'
        groups.write_text(json.dumps({'names': ['Группа']}))
        pins.write_text(json.dumps({'groups': {c.GROUP: 'Группа'}}))
        f.config['structure'] = dict(enabled=True, bidirectional=True, groups_allowlist_file=str(groups),
                                     group_ids_allowlist_file=str(pins), native_groups={c.GROUP: 'a'},
                                     list_roles={c.LID: {'kind': 'project', 'project_id': 'demo'}},
                                     projects={'demo': {'group': 'a', 'list_id': c.LID}},
                                     subgroups={}, journal_file='ai/structure.json')
        f.activation['snapshot'] = {'groups': copy.deepcopy(f.native.groups)}
        original = f.native.call
        def call(tool, args):
            if tool == 'get_reminder':
                return f.native.get(args['id'], c.LID)
            return original(tool, args)
        f.native.call = call
        f.save()
        first = m.sync(f.hub, f.config, True, native=f.native, reconcile=True)
        self.assertTrue(first['ok'], first)
        self.assertIn('absence_receipt', next(iter(f.config['projects']['demo']['history'].values())))
        before = (f.hub / 'ai/reminders-sync.json').read_bytes()
        with patch.object(e, 'capture', wraps=e.capture) as captured:
            result = m.sync(f.hub, f.config, True, native=f.native, reconcile=True, return_snapshot=True)
        self.assertTrue(result['ok'], result)
        self.assertTrue(result['final_snapshot']['complete'])
        self.assertEqual(captured.call_count, 1)
        self.assertEqual((f.hub / 'ai/reminders-sync.json').read_bytes(), before)
        self.assertEqual(f.native.writes, [])


if __name__ == '__main__':
    unittest.main()
