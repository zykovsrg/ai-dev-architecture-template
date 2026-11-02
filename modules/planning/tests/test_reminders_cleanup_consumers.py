import importlib.util
from pathlib import Path
import tempfile
import unittest

TESTS = Path(__file__).parent
SCRIPTS = TESTS.parent / 'scripts'
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

cleanup_tests = load('cleanup_fixture_for_consumers', TESTS / 'test_reminders_old_list_cleanup.py')
project_lists = load('project_lists_for_bulk_consumer', SCRIPTS / 'reminders_project_lists.py')


class NoNativeRead:
    def __init__(self): self.calls=[]
    def call(self, tool, args):
        self.calls.append((tool,args))
        raise AssertionError('old list must not be read after verified cleanup')


class CleanupConsumerTests(unittest.TestCase):
    def test_bulk_existing_project_list_accepts_receipt_without_reading_missing_parent_list(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            hub=Path(directory).resolve(); reference,parent_id,_=cleanup_tests.OldListCleanupContractTests.completed_receipt(hub)
            binding={'retired_parent': {'id':parent_id,'list_id':'00000000-0000-4000-8000-000000000001',
                        'snapshot': {'id':parent_id,'list_id':'00000000-0000-4000-8000-000000000001'}},
                     'retired_parent_cleanup':reference}
            native=NoNativeRead()
            project_lists.verify_bulk_retired_parent(hub,binding,{'lists':[]},{},native)
            self.assertEqual(native.calls,[])

    def test_bulk_existing_project_list_rejects_forged_receipt_before_native_read(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            hub=Path(directory).resolve(); reference,parent_id,_=cleanup_tests.OldListCleanupContractTests.completed_receipt(hub)
            reference['sha256']='0'*64
            binding={'retired_parent': {'id':parent_id,'list_id':'00000000-0000-4000-8000-000000000001',
                        'snapshot': {'id':parent_id,'list_id':'00000000-0000-4000-8000-000000000001'}},
                     'retired_parent_cleanup':reference}
            native=NoNativeRead()
            with self.assertRaisesRegex(ValueError,'cleanup_receipt_sha256_mismatch'):
                project_lists.verify_bulk_retired_parent(hub,binding,{'lists':[]},{},native)
            self.assertEqual(native.calls,[])

    def test_bulk_existing_project_list_rejects_missing_parent_without_receipt(self):
        binding={'retired_parent': {'id':'30000000-0000-4000-8000-000000000001',
                    'list_id':'00000000-0000-4000-8000-000000000001','snapshot':{}}}
        native=NoNativeRead()
        with self.assertRaisesRegex(ValueError,'retired_parent_list_missing_without_receipt'):
            project_lists.verify_bulk_retired_parent('/private/tmp',binding,{'lists':[]},{},native)
        self.assertEqual(native.calls,[])

    def test_bulk_existing_project_list_rejects_parent_list_reappearing_after_receipt(self):
        with tempfile.TemporaryDirectory(dir='/private/tmp') as directory:
            hub=Path(directory).resolve(); reference,parent_id,_=cleanup_tests.OldListCleanupContractTests.completed_receipt(hub)
            old_id='00000000-0000-4000-8000-000000000001'
            binding={'retired_parent': {'id':parent_id,'list_id':old_id,
                        'snapshot': {'id':parent_id,'list_id':old_id}}, 'retired_parent_cleanup':reference}
            native=NoNativeRead()
            with self.assertRaisesRegex(ValueError,'retired_parent_list_reappeared_after_cleanup'):
                project_lists.verify_bulk_retired_parent(hub,binding,{'lists':[{'id':old_id}]},{},native)
            self.assertEqual(native.calls,[])


if __name__ == '__main__': unittest.main()
