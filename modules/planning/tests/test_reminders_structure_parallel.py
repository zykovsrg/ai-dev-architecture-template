"""Ограниченное параллельное чтение полного снимка, без приложения."""
import copy
import threading
import unittest
from test_reminders_structure_batch import Native, L1, L2, snapshot, m

class ParallelDetailsTests(unittest.TestCase):
    def test_reads_overlap_and_preserve_exact_data(self):
        class Reader(Native):
            def __init__(self):
                super().__init__();self.lock=threading.Lock();self.gate=threading.Event();self.active=0;self.peak=0
            def call(self, tool, args):
                if tool!='find_reminders' or not args.get('detail'):return super().call(tool,args)
                with self.lock:
                    self.active+=1;self.peak=max(self.peak,self.active)
                    if self.active>=2:self.gate.set()
                try:
                    self.gate.wait(1)
                    return super().call(tool,args)
                finally:
                    with self.lock:self.active-=1
        native=Reader();actual=snapshot(native,detailed=True)
        self.assertEqual(actual,snapshot(Native(False),detailed=True))
        self.assertGreaterEqual(native.peak,2)

    def test_at_most_four_workers_and_isolated_helper_state(self):
        class Reader:
            def __init__(self):
                self.ids=[f'00000000-0000-0000-0000-{i:012d}' for i in range(100,108)]
                self.lock=threading.Lock();self.barrier=threading.Barrier(8);self.active=0;self.peak=0
                self._migration_detail_cache={'sentinel':'unchanged'};self._migration_batch_lists={'sentinel'}
            def call(self,tool,args):
                if tool=='list_lists':return dict(lists=[dict(id=lid,name=lid,group_id='g') for lid in self.ids],groups=[dict(id='g',name='Группа')],detailed_reminder_snapshot=True)
                if tool!='find_reminders':raise AssertionError(tool)
                if not args.get('detail'):return dict(count=0,reminders=[])
                with self.lock:self.active+=1;self.peak=max(self.peak,self.active)
                try:
                    try:self.barrier.wait(1)
                    except threading.BrokenBarrierError:pass
                    return dict(detail=True,count=0,reminders=[])
                finally:
                    with self.lock:self.active-=1
        native=Reader();value=m.snapshot(native,{lid:{} for lid in native.ids},set(native.ids),detailed=True)
        self.assertEqual(value['reminders'],{})
        self.assertGreaterEqual(native.peak,2)
        self.assertLessEqual(native.peak,4)
        self.assertEqual(native._migration_detail_cache,{'sentinel':'unchanged'})
        self.assertEqual(native._migration_batch_lists,{'sentinel'})

    def test_one_invalid_parallel_response_rejects_whole_snapshot(self):
        class Reader(Native):
            def __init__(self):
                super().__init__();self.details[L2]=[];self.summaries=self.project()
            def call(self,tool,args):
                value=super().call(tool,args)
                if tool=='find_reminders' and args.get('detail') and args['list']==L2:value['detail']=False
                return value
        with self.assertRaisesRegex(ValueError,'incomplete_detailed_snapshot'):
            snapshot(Reader(),detailed=True)

if __name__=='__main__':unittest.main()
