"""Настоящая квитанция отказа восстановления и доказанный перенос другого списка."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import test_reminders_cancel as cancelled_fixture

SCRIPTS=Path(os.environ.get('STRUCTURE_READ_CONTEXT_SCRIPTS',Path(__file__).resolve().parents[1]/'scripts'))
def load(name):
    spec=importlib.util.spec_from_file_location('read_context_'+name,SCRIPTS/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
m=load('reminders_structure');b=load('reminders_bidirectional')
GROUP='70000000-0000-4000-8000-000000000001'
ACCOUNT='60000000-0000-4000-8000-000000000001'


class StructureReadContextTests(unittest.TestCase):
    def setUp(self):
        f=cancelled_fixture.CancellationTests();f.setUp();self.addCleanup(f.doCleanups);self.fixture=f
        original=cancelled_fixture.m.verify_cancelled_link
        def capture(hub,row,link,binding,native,*args,**kwargs):
            if native.__class__.__name__=='FaithfulAfterCleanup' and not hasattr(self,'native'):
                self.native=copy.deepcopy(native)
            return original(hub,row,link,binding,native,*args,**kwargs)
        with patch.object(cancelled_fixture.m,'verify_cancelled_link',capture):
            f.test_old_refused_restore_future_status_uses_uuid_after_old_list_cleanup()
        self.hub=f.hub;self.config=copy.deepcopy(f.config);self.binding=self.config['projects']['demo'];self.rid=cancelled_fixture.RID
        self.cp=self.hub/'ai/reminders-sync.json';self.jp=self.hub/'ai/structure-journal.json';self.guard=self.hub/'ai/project-registry.md'
        self.native.active_groups=[dict(id=GROUP,name='Группа',account_id=ACCOUNT)]
        self.moved=next(pid for pid in self.config['projects'] if pid!='demo');lid=self.config['projects'][self.moved]['list_id']
        self.config['projects'][self.moved]['native_group_id']=GROUP
        structure=self.config['structure'];structure.update(enabled=True,bidirectional=True,journal_file='ai/structure-journal.json',native_groups={GROUP:'group'},subgroups={})
        initial=dict(lists={row['id']:{k:row[k] for k in ('id','name','account_id','group_id')} for row in self.native.active_lists},
                     groups={GROUP:dict(id=GROUP,name='Группа',account_id=ACCOUNT)},reminders={row['id']:copy.deepcopy(row) for row in self.native.active_rows})
        initial['lists'][lid]['group_id']=GROUP
        self.cp.write_text(m.encoded(self.config))
        originals={str(path.relative_to(self.hub)):path.read_text() for path in (self.cp,self.guard,self.hub/'ai/reminders-allowlist.json')}
        self.source=dict(version=2,status='pending',config=copy.deepcopy(self.config),originals=originals,snapshot=initial,
                         steps=[dict(kind='list',id=lid,group=None,projects=[self.moved])],files={},guards={name:text for name,text in originals.items() if name!='ai/reminders-sync.json'})
        digest=b.attestation(self.source['config'],originals,initial)
        pinned=copy.deepcopy(self.config);pinned['structure']['outgoing_intent_sha256']=digest
        after=copy.deepcopy(pinned);after['projects'][self.moved]['native_group_id']=None
        self.source['files']['ai/reminders-sync.json']=m.encoded(after)
        self.cp.write_text(m.encoded(pinned));self.jp.write_text(m.encoded(self.source))
        self.snapshot=copy.deepcopy(initial);self.snapshot['lists'][lid]['group_id']=None
        self.prefix=m.structure_prefix_module()
        self.rows_before=copy.deepcopy(self.native.active_rows)
    def context(self):
        try:return self.prefix.create_read_context(self.hub,self.source,self.snapshot)
        except ValueError as exc:self.fail(str(exc))
    def verify(self,context=None):
        config=copy.deepcopy(self.config);config['projects'][self.moved]['native_group_id']=None
        kwargs={} if context is None else dict(read_context=context)
        return m.verified_cancelled_ids(self.hub,'demo',self.binding,config,self.native,**kwargs)
    def assert_no_writes(self):
        self.assertFalse(any(isinstance(call,tuple) and call[0] in {'hub_cancel_reminder','hub_restore_reminder','manage_list','update_reminder'} for call in self.native.calls))
        self.assertNotIn('hub_cancel_status',self.native.calls)

    def test_context_reaches_real_forfeiture_without_changing_disk_or_subject(self):
        with self.assertRaisesRegex(ValueError,'cleanup_forfeiture_current_project_identity_changed'):self.verify()
        before=(self.cp.read_bytes(),self.jp.read_bytes(),copy.deepcopy(self.binding))
        context=self.context()
        try:ids=self.verify(context)
        except ValueError as exc:self.fail(str(exc))
        self.assertEqual(ids,{self.rid})
        self.assertEqual(before,(self.cp.read_bytes(),self.jp.read_bytes(),self.binding))
        self.assertEqual(self.native.active_rows,self.rows_before);self.assert_no_writes()

    def test_other_refused_uuid_reappearance_is_still_rejected(self):
        context=self.context();receipt=json.loads(Path(self.binding['retired_parent_cleanup']['path']).read_text())
        other=next(rid for rid in receipt['restore_refusal_ids'] if rid!=self.rid);row=self.native.active_rows[0]
        self.native.active_rows.append(dict(id=other,list_id=row['list_id'],list=row['list'],title='Вернувшаяся отменённая задача'))
        self.native.refresh_counts()
        with self.assertRaisesRegex(ValueError,'cleanup_forfeited_reminder_active'):self.verify(context)
        self.assert_no_writes()

    def test_tampered_context_capture_is_rejected(self):
        context=self.context();payload=json.loads(context._raw)
        payload['journal_raw']+='\n';object.__setattr__(context,'_raw',json.dumps(payload,ensure_ascii=False).encode())
        with self.assertRaisesRegex(ValueError,'structure_read_context_changed'):self.verify(context)
        self.assert_no_writes()

    def test_journal_changed_during_full_uuid_scan_is_rejected(self):
        before=self.jp.read_bytes()
        for change in ('content','line_endings'):
            with self.subTest(change=change):
                self.jp.write_bytes(before);context=self.context();call=self.native.call;changed=False
                def drift(tool,args):
                    nonlocal changed
                    result=call(tool,args)
                    if tool=='find_reminders' and not changed:
                        changed=True
                        self.jp.write_bytes(before+b'\n' if change=='content' else before.replace(b'\n',b'\r\n'))
                    return result
                with patch.object(self.native,'call',drift):
                    with self.assertRaisesRegex(ValueError,'structure_read_context_changed'):self.verify(context)
                self.assertTrue(changed);self.assert_no_writes()
        self.jp.write_bytes(before)

    def test_guard_changed_during_full_uuid_scan_is_rejected(self):
        before=self.guard.read_bytes()
        for change in ('content','line_endings'):
            with self.subTest(change=change):
                self.guard.write_bytes(before);context=self.context();call=self.native.call;changed=False
                def drift(tool,args):
                    nonlocal changed
                    result=call(tool,args)
                    if tool=='find_reminders' and not changed:
                        changed=True
                        self.guard.write_bytes(before+'Правка\n'.encode() if change=='content' else before.replace(b'\n',b'\r\n'))
                    return result
                with patch.object(self.native,'call',drift):
                    with self.assertRaisesRegex(ValueError,'structure_read_context_changed'):self.verify(context)
                self.assertTrue(changed);self.assert_no_writes()
        self.guard.write_bytes(before)

    def test_context_cannot_authorize_different_prefix_metadata(self):
        context=self.context();lid=self.config['projects'][self.moved]['list_id']
        next(row for row in self.native.active_lists if row['id']==lid)['group_id']=GROUP
        with self.assertRaisesRegex(ValueError,'structure_read_context_changed'):self.verify(context)
        self.assert_no_writes()

    def test_prefix_context_refuses_absence_of_forfeited_cancelled_series(self):
        source=copy.deepcopy(self.source);binding=source['config']['projects']['demo']
        binding['history']={'absent-history':dict(task_id=cancelled_fixture.TID,original_id=self.rid,absence_receipt={'proof':'separate-validation-required'})}
        source['originals']['ai/reminders-sync.json']=m.encoded(source['config'])
        digest=b.attestation(source['config'],source['originals'],source['snapshot'])
        current=copy.deepcopy(source['config']);current['structure']['outgoing_intent_sha256']=digest
        after=copy.deepcopy(current);after['projects'][self.moved]['native_group_id']=None;source['files']['ai/reminders-sync.json']=m.encoded(after)
        self.cp.write_text(m.encoded(current));self.jp.write_text(m.encoded(source))
        with self.assertRaisesRegex(ValueError,'structure_read_context_composition_unsupported'):
            self.prefix.create_read_context(self.hub,source,self.snapshot)
        self.assert_no_writes()

    def test_source_snapshot_must_attest_to_captured_config_pin(self):
        forged=copy.deepcopy(self.source);next(iter(forged['snapshot']['reminders'].values()))['title']='Подмена исходника'
        with self.assertRaisesRegex(ValueError,'structure_read_context_unattested'):
            self.prefix.create_read_context(self.hub,forged,self.snapshot)
        self.assert_no_writes()

if __name__=='__main__':unittest.main()
