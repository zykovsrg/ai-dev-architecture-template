import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).parents[1] / 'scripts' / 'reminders_old_list_cleanup.py'
spec = importlib.util.spec_from_file_location('cleanup_structure_refs_subject', SCRIPT)
cleanup = importlib.util.module_from_spec(spec); spec.loader.exec_module(cleanup)


def uuid_group(prefix, i): return f'{prefix}-0000-4000-8000-{i:012X}'


class StructureReferenceTests(unittest.TestCase):
    def context(self):
        candidate_ids = [uuid_group('00000000', i) for i in range(1, 19)]
        protected_ids = [uuid_group('10000000', i) for i in range(1, 77)]
        parents = [uuid_group('20000000', i) for i in range(1, 75)]
        subgroups = {'seo': {'list_id': candidate_ids[1], 'parent': 'hadassah'},
                     'promo': {'list_id': candidate_ids[2], 'parent': 'hadassah'},
                     'other': {'list_id': protected_ids[0], 'parent': 'kept'}}
        defaults = {'hadassah': candidate_ids[0], 'personal': protected_ids[1]}
        references = {'subgroups': {key: copy.deepcopy(subgroups[key]) for key in ('seo', 'promo')},
                      'group_default_lists': {'hadassah': candidate_ids[0]}}
        projects = {f'p{i}': {'retired_parent': {'id': parents[i], 'list_id': candidate_ids[i % 18]}}
                    for i in range(74)}
        config = {'projects': projects, 'structure': {
            'list_roles': {**{lid: {'kind': 'direct'} for lid in candidate_ids},
                           **{lid: {'kind': 'project'} for lid in protected_ids}},
            'subgroups': subgroups, 'group_default_lists': defaults,
            'projects': {'logical-project': {'group': 'hadassah', 'list_id': protected_ids[0]}}}}
        plan = {'candidate_list_ids': candidate_ids, 'retired_parent_ids': parents,
                'restore_refusal_ids': [], 'removed_structure_references': references}
        receipt = {'removed_structure_references': copy.deepcopy(references)}
        class Sync:
            @staticmethod
            def validate_binding_ids(_config): return None
        class Helper:
            @staticmethod
            def load_sync(): return Sync
        return config, plan, receipt, Helper, references, candidate_ids, protected_ids

    def call(self, mutate=None):
        config, plan, receipt, helper, references, candidate_ids, protected_ids = self.context()
        if mutate:
            mutate(config, plan, receipt)
        old = cleanup._modules; cleanup._modules = lambda: helper
        try:
            result = cleanup._final_config(config, plan,
                {'operation': '30000000-0000-4000-8000-000000000001', 'path': '/tmp/receipt.json', 'sha256': 'a' * 64}, receipt)
        finally:
            cleanup._modules = old
        return result, config, references, candidate_ids, protected_ids

    def test_final_config_archives_only_deleted_physical_references(self):
        result, original, references, candidate_ids, protected_ids = self.call()
        self.assertEqual(result['structure']['list_roles'].keys(), set(protected_ids))
        self.assertNotIn('seo', result['structure']['subgroups'])
        self.assertNotIn('promo', result['structure']['subgroups'])
        self.assertEqual(result['structure']['subgroups']['other'], original['structure']['subgroups']['other'])
        self.assertNotIn('hadassah', result['structure']['group_default_lists'])
        self.assertEqual(result['structure']['group_default_lists']['personal'], protected_ids[1])
        self.assertEqual(result['structure']['projects'], original['structure']['projects'])
        for project_id, binding in original['projects'].items():
            self.assertEqual(result['projects'][project_id].get('tasks'), binding.get('tasks'))
            self.assertEqual(result['projects'][project_id]['retired_parent'], binding['retired_parent'])

    def test_final_config_rejects_changed_subgroup_reference(self):
        def mutate(config, _plan, _receipt): config['structure']['subgroups']['seo']['parent'] = 'foreign'
        with self.assertRaisesRegex(ValueError, 'cleanup_structure_reference_cas_failed'):
            self.call(mutate)

    def test_final_config_rejects_unarchived_default_reference(self):
        def mutate(_config, _plan, receipt): receipt['removed_structure_references']['group_default_lists'].clear()
        with self.assertRaisesRegex(ValueError, 'cleanup_structure_reference_cas_failed'):
            self.call(mutate)


if __name__ == '__main__': unittest.main()
