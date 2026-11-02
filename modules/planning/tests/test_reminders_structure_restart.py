"""Безопасное обновление снимка прерванного переноса списков; приложение заменено временными данными."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
import test_reminders_project_list_reconcile as fixture
import test_reminders_recurrence as recurrence_fixture

SCRIPTS = Path(os.environ.get('STRUCTURE_RESTART_SCRIPTS', Path(__file__).resolve().parents[1] / 'scripts'))
spec = importlib.util.spec_from_file_location('structure_restart_subject', SCRIPTS / 'reminders_structure_restart.py')
r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)


class StructureRestartTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.ProjectListReconcileTests(); self.case.setUp(); self.addCleanup(self.case.doCleanups)
        self.hub = self.case.hub; self.native = self.case.native; self.config = copy.deepcopy(self.case.config)
        self.case.card('b')
        (self.hub / 'ai/project-cards/sibling.md').write_text('Project ID: sibling\nStatus: active\nprimary_archiproject: b\n')
        self.cp = self.hub / 'ai/reminders-sync.json'; self.jp = self.hub / self.config['structure']['journal_file']
        paths = [self.cp, self.hub/'ai/archiprojects.md', self.hub/'ai/project-registry.md', self.hub/'ai/lists.json', self.hub/'ai/groups.json', self.hub/'ai/group-ids.json', self.hub/'ai/project-cards/demo.md', self.hub/'ai/project-cards/sibling.md']
        self.originals = {p:p.read_text() for p in paths}
        initial = r.m.snapshot(self.native, self.config['structure']['list_roles'], {'lp','sibling'}, detailed=True, include_groups=True)
        result, steps, after = r.b.plan(r.m, self.hub, self.config, initial, copy.deepcopy(self.originals), {'demo':set(),'sibling':set()})
        self.assertTrue(result['ok'], result); self.assertEqual(len(steps), 2)
        self.journal = dict(version=2, status='pending', config=self.config, originals={str(p.relative_to(self.hub)):t for p,t in self.originals.items()}, snapshot=initial, steps=steps,
                            files={str(p.relative_to(self.hub)):t for p,t in after.items()}, guards={str(p.relative_to(self.hub)):t for p,t in self.originals.items() if p not in after})
        self.attest()
        self.old_journal = self.jp.read_bytes(); self.old_config = self.cp.read_bytes()
        self.native.lists[0]['group_id'] = 'n2'  # Один список уже перемещён, второй ещё нет.
        self.native.rows['lp'][0].update(notes='Новая заметка пользователя', due='2026-11-02T21:00:00', version='2')
        self.native.rows['lp'].append(dict(id='new-completed',title='Новое завершение',version='1',list_id='lp',completed=True))
    def attest(self):
        digest = r.b.attestation(self.journal['config'],self.journal['originals'],self.journal['snapshot'])
        pinned = copy.deepcopy(self.config); pinned['structure']['outgoing_intent_sha256'] = digest
        final = json.loads(self.journal['files']['ai/reminders-sync.json']); final['structure']['outgoing_intent_sha256'] = digest
        self.journal['files']['ai/reminders-sync.json'] = r.m.encoded(final)
        self.cp.write_text(r.m.encoded(pinned)); self.jp.write_text(r.m.encoded(self.journal))
    def preview(self):
        try:return r.preview(self.hub, native=self.native)
        except ValueError as exc:self.fail(str(exc))
    def apply(self, preview):return r.apply(preview['plan'], preview['sha256'], native=self.native)
    def writes(self):return [(tool,args) for tool,args in self.native.calls if tool in {'manage_list','update_reminder','create_reminder'}]
    def state_unchanged(self):
        self.assertEqual(self.cp.read_bytes(),self.old_config);self.assertEqual(self.jp.read_bytes(),self.old_journal)

    def test_prefix_restart_preserves_external_fields_and_normal_recovery_moves_only_suffix(self):
        rows = copy.deepcopy(self.native.rows); tasks = copy.deepcopy(self.config['projects'])
        preview = self.preview(); self.assertEqual(preview['prefix'],1); self.state_unchanged()
        saved = json.loads(Path(preview['plan']).read_text()); self.assertEqual(saved['before_journal'].encode(),self.old_journal)
        result = self.apply(preview); self.assertTrue(result['ok']); self.assertEqual(self.writes(),[])
        self.assertEqual(self.native.rows,rows)
        staged = json.loads(self.cp.read_text()); self.assertEqual(staged['projects'],tasks)
        journal = json.loads(self.jp.read_text()); self.assertEqual(journal['steps'],self.journal['steps'])
        self.assertEqual(journal['snapshot']['reminders'], {row['id']:row for values in rows.values() for row in values})
        recovered = fixture.m.reconcile_structure(self.hub,staged,True,self.native)
        self.assertTrue(recovered['ok'],recovered)
        self.assertEqual(self.native.rows,rows)
        self.assertEqual(self.writes(), [('manage_list',dict(action='update',list='sibling',group='n2',expected_group_id='n1'))])

    def test_prefix_proof_preserves_real_stopped_series_receipts_on_other_project(self):
        f=recurrence_fixture.RecurrenceTests();f.setUp();self.addCleanup(f.doCleanups)
        mover='00000000-0000-0000-0000-000000000031';move_task='00000000-0000-0000-0000-000000000032';destination='00000000-0000-0000-0000-000000000033'
        rf=recurrence_fixture
        (f.hub/'projects/mover').mkdir();(f.hub/'ai/project-cards').mkdir()
        registry=''
        for pid,group in [('demo','a'),('mover','b')]:
            (f.hub/'ai/project-cards'/(pid+'.md')).write_text(f'Project ID: {pid}\nStatus: active\nprimary_archiproject: {group}\n')
            registry+=f'## {pid}\nStatus: active\nPath: {f.hub}/projects/{pid}\nCard: ai/project-cards/{pid}.md\n'
        (f.hub/'ai/project-registry.md').write_text(registry)
        f.native.lists.append(dict(id=mover,name='Перенос',account_id=rf.ACCOUNT,group_id=rf.GROUP))
        f.native.groups.append(dict(id=destination,name='Назначение',account_id=rf.ACCOUNT))
        f.native.rows[move_task]=dict(id=move_task,title='Задача переносимого проекта',version='1',completed=False,list='Перенос',list_id=mover)
        f.config['projects']['mover']=dict(layout='project_list',list_id=mover,list_name='Перенос',account_id=rf.ACCOUNT,native_group_id=rf.GROUP,tasks={'move':dict(reminder_id=move_task)},history={})
        (f.hub/'ai/reminders-allowlist.json').write_text(json.dumps({'names':['Работа','Перенос']}));f.save()
        f.historical();f.retire_series();f.missing()
        config=f.read()
        (f.hub/'ai/archiprojects.md').write_text(''.join(f'## {gid}\n```yaml\nid: {gid}\nname: {gid}\nstatus: active\nkind: group\n```\n' for gid in ('a','b')))
        (f.hub/'ai/groups.json').write_text(json.dumps({'names':['Группа','Назначение']}))
        (f.hub/'ai/group-ids.json').write_text(json.dumps({'groups':{rf.GROUP:'Группа',destination:'Назначение'}}))
        config['structure']=dict(enabled=True,bidirectional=True,groups_allowlist_file=str(f.hub/'ai/groups.json'),group_ids_allowlist_file=str(f.hub/'ai/group-ids.json'),native_groups={rf.GROUP:'a',destination:'b'},list_roles={rf.LID:dict(kind='project',project_id='demo'),mover:dict(kind='project',project_id='mover')},projects={'demo':dict(group='a',list_id=rf.LID),'mover':dict(group='a',list_id=mover)},subgroups={},journal_file='ai/structure-journal.json')
        cp=f.hub/'ai/reminders-sync.json';cp.write_text(r.m.encoded(config))
        class Reader:
            def call(self,tool,args):
                if tool=='get_reminder':return copy.deepcopy(f.native.rows[args['id']])
                return f.native.call(tool,args)
        native=Reader();initial=r.m.snapshot(native,config['structure']['list_roles'],{'Работа','Перенос'},detailed=True,include_groups=True)
        paths=[cp,f.hub/'ai/archiprojects.md',f.hub/'ai/project-registry.md',f.hub/'ai/reminders-allowlist.json',f.hub/'ai/groups.json',f.hub/'ai/group-ids.json',f.hub/'ai/project-cards/demo.md',f.hub/'ai/project-cards/mover.md']
        originals={p:p.read_text() for p in paths};verified={pid:r.m.verified_cancelled_ids(f.hub,pid,binding,config,native) for pid,binding in config['projects'].items()}
        result,steps,after=r.b.plan(r.m,f.hub,config,initial,copy.deepcopy(originals),verified);self.assertTrue(result['ok'],result)
        j=dict(version=2,status='pending',config=config,originals={str(p.relative_to(f.hub)):text for p,text in originals.items()},snapshot=initial,steps=steps,files={str(p.relative_to(f.hub)):text for p,text in after.items()},guards={str(p.relative_to(f.hub)):text for p,text in originals.items() if p not in after})
        digest=r.b.attestation(config,j['originals'],initial);pinned=copy.deepcopy(config);pinned['structure']['outgoing_intent_sha256']=digest
        final=json.loads(j['files']['ai/reminders-sync.json']);final['structure']['outgoing_intent_sha256']=digest;j['files']['ai/reminders-sync.json']=r.m.encoded(final)
        cp.write_text(r.m.encoded(pinned));jp=f.hub/'ai/structure-journal.json';jp.write_text(r.m.encoded(j))
        f.native.lists[1]['group_id']=destination
        try:preview=r.preview(f.hub,native=native)
        except ValueError as exc:self.fail(str(exc))
        self.assertEqual(preview['prefix'],1)
        self.assertTrue(r.apply(preview['plan'],preview['sha256'],native=native)['ok'])
        staged=json.loads(cp.read_text());self.assertEqual(staged['projects']['demo'],config['projects']['demo'])
        recovered=r.m.reconcile_structure(f.hub,staged,True,native);self.assertTrue(recovered['ok'],recovered)
        self.assertEqual(recovered['config']['projects']['demo'],config['projects']['demo']);self.assertEqual(f.native.writes,[])

    def test_prefix_context_refuses_moving_any_receipt_subject(self):
        snapshot=r.m.snapshot(self.native,self.config['structure']['list_roles'],{'lp','sibling'},detailed=True,include_groups=True)
        for proof in ('cancellation','external_retirement','absence_receipt','confirmation_receipt'):
            with self.subTest(proof=proof):
                config=copy.deepcopy(self.config)
                if proof in ('cancellation','external_retirement'):config['projects']['demo']['tasks']['t'][proof]={'proof':'exists'}
                else:config['projects']['demo']['history']['past']={proof:{'proof':'exists'}}
                with self.assertRaisesRegex(ValueError,'structure_prefix_receipt_project_move'):
                    r.prefix_context.verification_config(config,self.journal['snapshot'],self.journal['steps'],snapshot)
        self.state_unchanged();self.assertEqual(self.writes(),[])

    def test_restart_refuses_reminder_steps_noop_lists_and_repeated_list_ids(self):
        original = copy.deepcopy(self.journal)
        for kind in ('reminder','noop','duplicate'):
            with self.subTest(kind=kind):
                self.journal=copy.deepcopy(original)
                if kind=='reminder':self.journal['steps'][0]=dict(kind='reminder',id='task',list='sibling',projects=['demo'])
                if kind=='noop':self.journal['steps'][0]['group']='n1'
                if kind=='duplicate':self.journal['steps'].append(copy.deepcopy(self.journal['steps'][0]))
                self.attest()
                with self.assertRaisesRegex(ValueError,'structure_restart_list_only'):
                    r.preview(self.hub,native=self.native)
                self.assertEqual(self.writes(),[])

    def test_unknown_structural_state_cannot_be_rebased(self):
        self.native.lists[1]['group_id']=None
        with self.assertRaisesRegex(ValueError,'structure_restart_unknown_prefix'):r.preview(self.hub,native=self.native)
        self.state_unchanged();self.assertEqual(self.writes(),[])

    def test_surviving_reminder_parent_change_cannot_be_rebased(self):
        self.native.rows['lp'][1]['parent_id']=None
        with self.assertRaisesRegex(ValueError,'structure_restart_task_moved'):r.preview(self.hub,native=self.native)
        self.state_unchanged();self.assertEqual(self.writes(),[])

    def test_preview_requires_two_equal_fresh_full_snapshots(self):
        call=self.native.call; count=0
        def drift(tool,args):
            nonlocal count
            if tool=='list_lists':
                count+=1
                if count==2:self.native.rows['lp'][0]['notes']='Пользователь редактирует дальше'
            return call(tool,args)
        with patch.object(self.native,'call',drift):
            with self.assertRaisesRegex(ValueError,'structure_restart_snapshot_changed'):r.preview(self.hub,native=self.native)
        self.assertGreaterEqual(count,2);self.state_unchanged()

    def test_changed_guard_blocks_apply_without_local_or_native_writes(self):
        preview=self.preview();guard=self.hub/'ai/project-cards/demo.md';guard.write_text(guard.read_text()+'Новая правка\n')
        with self.assertRaisesRegex(ValueError,'structure_restart_guard_changed'):self.apply(preview)
        self.state_unchanged();self.assertEqual(self.writes(),[])

    def test_guard_changed_during_plan_is_rechecked_before_first_write(self):
        preview=self.preview();plan=r.b.plan;guard=self.hub/'ai/project-cards/demo.md'
        def change(*args,**kwargs):
            result=plan(*args,**kwargs);guard.write_text(guard.read_text()+'Правка во время расчёта\n');return result
        with patch.object(r.b,'plan',change):
            with self.assertRaisesRegex(ValueError,'structure_restart_guard_changed'):self.apply(preview)
        self.state_unchanged();self.assertEqual(self.writes(),[])

    def test_native_drift_during_plan_blocks_apply_before_first_local_write(self):
        preview=self.preview();plan=r.b.plan
        def change(*args,**kwargs):
            result=plan(*args,**kwargs);self.native.rows['lp'][0]['notes']='Правка во время расчёта';return result
        with patch.object(r.b,'plan',change):
            with self.assertRaisesRegex(ValueError,'structure_restart_snapshot_changed'):self.apply(preview)
        self.state_unchanged();self.assertEqual(self.writes(),[])
        self.assertEqual(self.native.rows['lp'][0]['notes'],'Правка во время расчёта')

    def test_partial_pair_recovers_only_same_plan_and_equal_fresh_snapshot(self):
        preview=self.preview();write=r.m.atomic_write
        def crash(path,text):
            write(path,text)
            if path==self.jp:raise OSError('crash after journal')
        with patch.object(r.m,'atomic_write',crash):
            with self.assertRaisesRegex(OSError,'crash after journal'):self.apply(preview)
        self.assertEqual(self.cp.read_bytes(),self.old_config);self.assertNotEqual(self.jp.read_bytes(),self.old_journal)
        blocked=fixture.m.reconcile_structure(self.hub,json.loads(self.cp.read_text()),True,self.native)
        self.assertFalse(blocked['ok']);self.assertIn('structure_intent_unattested',str(blocked));self.assertEqual(self.writes(),[])
        notes=self.native.rows['lp'][0]['notes'];self.native.rows['lp'][0]['notes']='Ещё новая заметка'
        with self.assertRaisesRegex(ValueError,'structure_restart_snapshot_changed'):self.apply(preview)
        self.assertEqual(self.cp.read_bytes(),self.old_config)
        self.native.rows['lp'][0]['notes']=notes
        self.assertTrue(self.apply(preview)['ok']);self.assertTrue(self.apply(preview)['ok']);self.assertEqual(self.writes(),[])

    def test_normal_recovery_resumes_after_final_config_write_but_rejects_foreign_pin(self):
        preview=self.preview();self.apply(preview);write=r.m.atomic_write
        def crash(path,text):
            write(path,text)
            if path==self.cp:
                value=json.loads(text)
                if value['projects']['sibling']['native_group_id']=='n2' and value['structure'].get('outgoing_completed_sha256')!=value['structure'].get('outgoing_intent_sha256'):
                    raise OSError('crash after result config')
        with patch.object(r.m,'atomic_write',crash):
            stopped=r.m.reconcile_structure(self.hub,json.loads(self.cp.read_text()),True,self.native)
        self.assertFalse(stopped['ok']);self.assertIn('crash after result config',str(stopped))
        final_config=self.cp.read_bytes();writes=copy.deepcopy(self.writes())
        foreign=json.loads(final_config);foreign['projects']['demo']['native_group_id']='foreign-pin';self.cp.write_text(r.m.encoded(foreign))
        altered=self.cp.read_bytes();blocked=r.m.reconcile_structure(self.hub,foreign,True,self.native)
        self.assertFalse(blocked['ok']);self.assertEqual(self.cp.read_bytes(),altered);self.assertEqual(self.writes(),writes)
        self.cp.write_bytes(final_config)
        resumed=r.m.reconcile_structure(self.hub,json.loads(final_config),True,self.native)
        self.assertTrue(resumed['ok'],resumed);self.assertEqual(self.writes(),writes)
        self.assertEqual(resumed['config']['projects']['demo']['native_group_id'],'n2')

    def test_existing_mixed_list_and_reminder_journal_recovers_suffix(self):
        config=copy.deepcopy(self.config)
        config['projects']={pid:dict(parent_id=parent,list_id=lid,list_name=lid,tasks={'t':dict(reminder_id=child)}) for pid,parent,child,lid in [('demo','p1','t1','l1'),('sibling','p2','t2','l2')]}
        config['structure'].update(list_roles={lid:dict(kind='direct') for lid in ('l1','l2','l3')},projects={'demo':dict(group='a',list_id='l1'),'sibling':dict(group='a',list_id='l2')},group_default_lists={'b':'l3'})
        self.cp.write_text(r.m.encoded(config))
        self.native.lists=[dict(id=lid,name=lid,group_id=group,account_id='account') for lid,group in [('l1','n1'),('l2','n1'),('l3','n2')]]
        self.native.rows={'l1':[dict(id='p1',title='Первый',version='1',list_id='l1'),dict(id='t1',title='Дело',version='1',list_id='l1',parent_id='p1')],
                          'l2':[dict(id='p2',title='Второй',version='1',list_id='l2'),dict(id='t2',title='Дело',version='1',list_id='l2',parent_id='p2'),dict(id='unbound',title='Личное',version='1',list_id='l2')],'l3':[]}
        self.native.call('list_lists',{})
        (self.hub/'ai/lists.json').write_text(json.dumps(['l1','l2','l3']))
        originals={path:path.read_text() for path in self.originals};initial=r.m.snapshot(self.native,config['structure']['list_roles'],{'l1','l2','l3'},detailed=True)
        result,steps,after=r.b.plan(r.m,self.hub,config,initial,copy.deepcopy(originals),{'demo':set(),'sibling':set()});self.assertTrue(result['ok'],result)
        self.assertEqual(steps[0]['kind'],'list');self.assertTrue(any(step['kind']=='reminder' for step in steps))
        j=dict(version=2,status='pending',config=config,originals={str(path.relative_to(self.hub)):text for path,text in originals.items()},snapshot=initial,steps=steps,files={str(path.relative_to(self.hub)):text for path,text in after.items()},guards={str(path.relative_to(self.hub)):text for path,text in originals.items() if path not in after})
        digest=r.b.attestation(config,j['originals'],initial);pinned=copy.deepcopy(config);pinned['structure']['outgoing_intent_sha256']=digest
        final=json.loads(j['files']['ai/reminders-sync.json']);final['structure']['outgoing_intent_sha256']=digest;j['files']['ai/reminders-sync.json']=r.m.encoded(final)
        self.cp.write_text(r.m.encoded(pinned));self.jp.write_text(r.m.encoded(j));self.native.lists[0]['group_id']='n2'
        original_call=self.native.call
        def update(tool,args):
            if tool!='update_reminder':return original_call(tool,args)
            self.native.calls.append((tool,copy.deepcopy(args)))
            row=next(row for rows in self.native.rows.values() for row in rows if row['id']==args['id'])
            self.assertEqual(row['version'],args['version'])
            if 'parent_id' in args:row['parent_id']=args['parent_id']
            if 'list' in args:
                self.native.rows[row['list_id']].remove(row);row['list_id']=args['list'];self.native.rows[args['list']].append(row)
            row['version']=str(int(row['version'])+1);return copy.deepcopy(row)
        with patch.object(self.native,'call',update):resumed=r.m.reconcile_structure(self.hub,pinned,True,self.native)
        self.assertTrue(resumed['ok'],resumed)
        self.assertEqual(resumed['config']['projects']['sibling']['list_id'],'l3')
        self.assertEqual({row['id'] for row in self.native.rows['l3']},{'p2','t2'})
        self.assertFalse(any(tool=='manage_list' for tool,args in self.native.calls))

    def test_changed_plan_cannot_rewrite_task_baseline_even_with_new_checksum(self):
        preview=self.preview();path=Path(preview['plan']);saved=json.loads(path.read_text())
        after=json.loads(saved['after_config']);after['projects']['demo']['tasks']['t']['forged']='Недопустимая база'
        saved['after_config']=r.m.encoded(after);path.write_text(json.dumps(saved,ensure_ascii=False))
        checksum=hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'structure_restart_plan_changed'):r.apply(path,checksum,native=self.native)
        self.state_unchanged();self.assertEqual(self.writes(),[])

    def test_preview_uses_common_authority_lock(self):
        outcomes=[]
        def competing():
            try:r.preview(self.hub,native=self.native)
            except Exception as exc:outcomes.append(exc)
        with r.sync.authority_module().locked(self.hub):
            thread=threading.Thread(target=competing);thread.start();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertEqual(len(outcomes),1)
        self.assertIsInstance(outcomes[0],BlockingIOError);self.state_unchanged()

if __name__=='__main__':unittest.main()
