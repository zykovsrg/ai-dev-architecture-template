"""Переход архивов проверяется только на синтетическом Хабе."""
import copy, importlib.util, json, os, shutil, sys, unittest
from pathlib import Path
from unittest.mock import patch
from test_reminders_archive import ArchiveTests, a, M

HELPER = Path(os.environ.get('AUTHORITY_ARCHIVE_SOURCE', str(a.__file__))).with_name('reminders_authority_archive.py')

def helper():
    assert HELPER.exists(), 'Отсутствует проверенный переход к источнику состояния'
    spec=importlib.util.spec_from_file_location('authority_archive_test', HELPER)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

class ArchiveAuthorityTests(ArchiveTests):
    def setUp(self):
        # Синтетический Хаб получает только исходный код, без данных установленного Хаба.
        with patch('test_reminders_archive.REAL',Path(__file__).parents[2]/'tasks'):
            super().setUp()
        for source in Path(a.__file__).parent.glob('*.py'):
            shutil.copyfile(source,self.h/'scripts'/source.name)
        sys.modules.pop('hub_reminders_task_gateway',None)
    # Унаследованные проверки запускаются отдельно; здесь только новые сценарии.
    def activate(self):
        self.aa=helper();v=self.aa.preview(self.h,'Главная копия в Напоминаниях; удаление отменяет с историей.',self.native)
        self.aa.apply(v['plan'],v['sha256'],True,self.native)
        return v
    def test_activation_receipt_is_required(self):
        aa=helper();c=self.current();c['task_authority']=dict(mode='reminders',deletions='cancel',journal='ai/reminders-authority/00000000-0000-4000-8000-000000000000',sha256='0'*64)
        with self.assertRaises((ValueError,FileNotFoundError)):aa.validate_activation(self.h,c)
    def test_activation_checks_intent_and_final_state(self):
        v=self.activate();c=self.current();plan=self.aa.validate_activation(self.h,c)
        self.assertTrue(plan['statement']);self.assertEqual(plan['deletion_policy'],'cancel')
        state=Path(v['plan']).with_name('state.json');s=json.loads(state.read_text());s['approved']=False;M.atomic_json(state,s)
        with self.assertRaisesRegex(ValueError,'activation'):self.aa.validate_activation(self.h,c)
    def test_activation_cas_rejects_concurrent_config(self):
        aa=helper();v=aa.preview(self.h,'Удаление отменяет с историей.',self.native);c=self.current();c['user_change']='KEEP';self.savec(c)
        with self.assertRaisesRegex(ValueError,'config'):aa.apply(v['plan'],v['sha256'],True,self.native)
        self.assertEqual(self.current()['user_change'],'KEEP');self.assertNotIn('task_authority',self.current())
    def test_activation_refuses_context_change(self):
        self.archived();p=self.h/'projects/demo/ai/future-tasks.md';p.write_text(p.read_text()+'\nПодменённый контекст\n')
        aa=helper()
        with self.assertRaisesRegex(ValueError,'context|task_file'):aa.preview(self.h,'Главная копия в приложении.',self.native)
    def test_adopted_archive_accepts_task_changes_without_rewriting_receipt(self):
        old,_=self.archived();oldbytes=old.read_bytes();self.activate();c=self.current()
        self.native.rows[self.rid].update(title='Новое название',due='2026-11-02',completed=False,notes='Новая заметка')
        target=self.h/'projects/demo/ai/future-tasks.md';target.write_text(target.read_text().replace('Написать текст','Новое название').replace('Status: done','Status: ready').replace('Запланировано: 2026-10-28.','Запланировано: 2026-11-02.'))
        c['projects']['demo']['tasks'][self.tid].update(last_remote_title='Новое название',last_completed=False);self.savec(c)
        self.assertTrue(a.verify_archived(self.h,c,'demo',a.snapshot(self.native)))
        self.assertEqual(old.read_bytes(),oldbytes);self.assertEqual(self.aa.project_path(self.h,c,'demo'),self.h/'projects/demo')
    def test_adopted_archive_keeps_group_account_and_pins(self):
        self.archived();self.activate();c=self.current();self.native.groups[-1]['account_id']='foreign'
        with self.assertRaisesRegex(ValueError,'group'):a.verify_archived(self.h,c,'demo',a.snapshot(self.native))
    def test_adopted_archive_rejects_pin_tampering(self):
        self.archived();self.activate();c=self.current();pins=json.loads((self.h/'ai/pins.json').read_text());pins['groups'].pop(self.native.groups[-1]['id']);M.atomic_json(self.h/'ai/pins.json',pins)
        with self.assertRaisesRegex(ValueError,'pin'):a.verify_archived(self.h,c,'demo',a.snapshot(self.native))
    def test_adopted_archive_rejects_identity_tampering(self):
        self.archived();self.activate();c=self.current();c['projects']['demo']['tasks'][self.tid]['reminder_id']='foreign'
        with self.assertRaisesRegex(ValueError,'identity|binding'):a.read_receipt(self.h,c,'demo')
    def test_corrupted_anchor_is_error(self):
        self.archived();v=self.activate();c=self.current();s=json.loads(Path(v['plan']).with_name('state.json').read_text());ref=s['archives']['demo'];anchor=self.h/ref['journal'];anchor.write_text('{}')
        with self.assertRaisesRegex(ValueError,'anchor'):a.read_receipt(self.h,c,'demo')
    def test_missing_anchor_retains_legacy_checks(self):
        self.archived();v=self.activate();s=json.loads(Path(v['plan']).with_name('state.json').read_text());s['archives'].pop('demo');M.atomic_json(Path(v['plan']).with_name('state.json'),s)
        self.native.rows[self.rid]['title']='Изменено'
        with self.assertRaisesRegex(ValueError,'content_changed'):a.verify_archived(self.h,self.current(),'demo',a.snapshot(self.native))
    def test_adopted_restore_refuses_before_any_write(self):
        self.archived();self.activate();before=(self.h/'ai/reminders-sync.json').read_bytes();calls=len(self.native.calls)
        with self.assertRaisesRegex(ValueError,'authority_restore_requires_new_plan'):a.restore(self.h,'demo','old-token',True,self.native)
        self.assertEqual(before,(self.h/'ai/reminders-sync.json').read_bytes());self.assertFalse(any(t.startswith('manage') for t,_ in self.native.calls[calls:]))
    def test_new_archive_creates_authority_anchor(self):
        self.activate();p,t=self.plan();self.run_apply(p,t);c=self.current()
        receipt=a.read_receipt(self.h,c,'demo');self.assertTrue(self.aa.archive_adopted(self.h,c,'demo',*receipt))
        self.native.rows[self.rid]['title']='Изменено после архива'
        self.assertTrue(a.verify_archived(self.h,c,'demo',a.snapshot(self.native)))
    def test_activation_rejects_bound_list_account_change(self):
        aa=helper();self.native.lists[self.lid]['account_id']='foreign'
        with self.assertRaisesRegex(ValueError,'identity'):aa.preview(self.h,'Главная копия в приложении.',self.native)
    def test_activation_rejects_changed_scope_permissions(self):
        aa=helper();v=aa.preview(self.h,'Главная копия в приложении.',self.native)
        (self.h/'ai/lists.json').write_text('{"names": []}')
        with self.assertRaisesRegex(ValueError,'permission'):aa.apply(v['plan'],v['sha256'],True,self.native)
        self.assertNotIn('task_authority',self.current())
    def test_activation_rejects_plan_checksum_change(self):
        v=self.activate();plan=Path(v['plan']);plan.write_text(plan.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'checksum'):self.aa.validate_activation(self.h,self.current())
    def test_activation_rejects_missing_original_statement(self):
        v=self.activate();plan=Path(v['plan']);p=json.loads(plan.read_text());p['statement']='';M.atomic_json(plan,p)
        c=self.current();c['task_authority']['sha256']=a.digest(plan.read_bytes())
        state=plan.with_name('state.json');st=json.loads(state.read_text());st.update(statement='',plan_sha256=c['task_authority']['sha256']);M.atomic_json(state,st)
        with self.assertRaisesRegex(ValueError,'intent'):self.aa.validate_activation(self.h,c)
    def test_activation_resume_after_configuration_write(self):
        aa=helper();v=aa.preview(self.h,'Главная копия в приложении.',self.native);atomic=M.atomic_json;once=[True]
        def fail(path,value):
            result=atomic(path,value)
            if path.name=='reminders-sync.json' and once[0]:once[0]=False;raise RuntimeError('configuration written')
            return result
        with patch.object(a,'load_sync',return_value=M),patch.object(aa,'archive',return_value=a),patch.object(M,'atomic_json',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'configuration written'):aa.apply(v['plan'],v['sha256'],True,self.native)
            result=aa.apply(v['plan'],v['sha256'],True,self.native)
        self.assertEqual(result['phase'],'complete');aa.validate_activation(self.h,self.current())
    def test_activation_preserves_historical_archive_checksum(self):
        p,t=self.archived();v=self.activate();p.write_text(p.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'checksum'):a.read_receipt(self.h,self.current(),'demo')
    def test_adopted_external_retirement_uses_completed_provenance(self):
        self.archived();self.activate();c=self.current();operation='11111111-1111-4111-8111-111111111111'
        folder=self.h/'ai/reminders-external-retirements'/operation;folder.mkdir(parents=True)
        link=copy.deepcopy(c['projects']['demo']['tasks'][self.tid])
        item=dict(project_id='demo',task_id=self.tid,reminder_id=self.rid,project_path=str(self.h/'projects/demo'),link=link)
        plan=dict(version=1,kind='external_retirement',operation=operation,hub=str(self.h),items=[item],projects={'demo':{}})
        M.atomic_json(folder/'plan.json',plan);sha=a.digest((folder/'plan.json').read_bytes())
        M.atomic_json(folder/'state.json',dict(sha256=sha,approved=True,phase='complete'))
        c['projects']['demo']['tasks'][self.tid]['external_retirement']=dict(kind='external_retirement',operation=operation,plan_sha256=sha,reminder_id=self.rid)
        c['external_retirements_completed']={'demo':{operation:sha}};self.savec(c)
        self.assertEqual(self.aa.project_path(self.h,c,'demo'),self.h/'projects/demo')
        state=json.loads((folder/'state.json').read_text());state['phase']='intent';M.atomic_json(folder/'state.json',state)
        with self.assertRaisesRegex(ValueError,'retirement'):self.aa.project_path(self.h,c,'demo')
    def test_adopted_archive_accepts_proven_recurrence_lineage(self):
        self.archived();self.activate();c=self.current();newrid='22222222-2222-4222-8222-222222222222'
        c['projects']['demo']['tasks'][self.tid]['reminder_id']=newrid
        c['projects']['demo']['history'][self.rid]=dict(project_id='demo',task_id=self.tid,original_id=newrid)
        self.assertEqual(self.aa.project_path(self.h,c,'demo'),self.h/'projects/demo')
        c['projects']['demo']['history'][self.rid]['task_id']='foreign'
        with self.assertRaisesRegex(ValueError,'identity'):self.aa.project_path(self.h,c,'demo')
    def test_activation_rejects_truncated_list_metadata(self):
        aa=helper();call=self.native.call
        def incomplete(tool,args):
            data=call(tool,args)
            if tool=='list_lists':data['has_more']=True
            return data
        self.native.call=incomplete
        with self.assertRaisesRegex(ValueError,'incomplete'):aa.preview(self.h,'Главная копия в приложении.',self.native)
    def test_activation_records_observed_missing_separately_from_statement(self):
        aa=helper();self.native.rows.clear();statement='Удаление отменяет с историей.'
        v=aa.preview(self.h,statement,self.native);plan=json.loads(Path(v['plan']).read_text())
        self.assertEqual(plan['statement'],statement)
        self.assertEqual(plan.get('initial_missing'),[dict(project_id='demo',task_id=self.tid,reminder_id=self.rid)])
    def test_activation_rejects_existing_uuid_in_foreign_list(self):
        aa=helper();other='33333333-3333-4333-8333-333333333333'
        self.native.lists[other]=dict(id=other,name='Другая',group_id=self.gid,account_id=self.account)
        self.native.rows[self.rid]['list_id']=other
        with self.assertRaisesRegex(ValueError,'identity'):aa.preview(self.h,'Главная копия в приложении.',self.native)
    def test_completed_new_archive_replay_accepts_app_changes(self):
        self.activate();p,t=self.plan();self.run_apply(p,t)
        c=self.current();c['projects']['demo']['tasks'][self.tid]['last_completed']=False
        newrid='44444444-4444-4444-8444-444444444444';newtid='TASK-demo-20261030-002'
        c['projects']['demo']['tasks'][newtid]=dict(reminder_id=newrid,pending_import=True);self.savec(c)
        task=self.h/'projects/demo/ai/future-tasks.md';task.write_text(task.read_text().replace('Написать текст','Новая задача')+'\n### '+newtid+' — Ещё задача\n\nStatus: ready\n')
        self.native.rows[self.rid]['title']='Новая задача'
        self.native.rows[newrid]=dict(id=newrid,title='Ещё задача',list_id=self.lid,version='v1',completed=False)
        self.assertEqual(self.run_apply(p,t)['phase'],'complete')
    def test_new_archive_uses_internal_checked_writer(self):
        self.activate();p,t=self.plan();parser=M.parser_for(self.h)
        with patch.object(a,'load_sync',return_value=M),patch.object(M,'parser_for',return_value=parser),patch.object(parser,'write_task_file',wraps=parser.write_task_file) as writer,patch('subprocess.run',side_effect=AssertionError('Внешняя запись под общей блокировкой')):
            self.run_apply(p,t)
        self.assertEqual(writer.call_count,1)
        self.assertEqual(writer.call_args.args[:3],(self.h,'demo','future'))
    def test_anchor_cannot_replace_activation_historical_baseline(self):
        p,t=self.archived();v=self.activate();c=self.current()
        historic=p.with_name('state.json');old=json.loads(historic.read_text());old['projects']['demo']['files_after']['future-tasks.md']+='\nЧужой контекст\n';M.atomic_json(historic,old)
        target=self.h/'projects/demo/ai/future-tasks.md';target.write_text(old['projects']['demo']['files_after']['future-tasks.md'])
        activation=Path(v['plan']).with_name('state.json');state=json.loads(activation.read_text());anchor=self.h/state['archives']['demo']['journal'];body=json.loads(anchor.read_text());body['historical_saved_sha256']=a.digest(old['projects']['demo']);M.atomic_json(anchor,body)
        state['archives']['demo']['sha256']=a.digest(anchor.read_bytes());M.atomic_json(activation,state)
        with self.assertRaisesRegex(ValueError,'anchor'):a.read_receipt(self.h,c,'demo')
    def test_adopted_archive_preserves_historical_owner(self):
        oldrid='55555555-5555-4555-8555-555555555555';self.c['projects']['demo']['history'][oldrid]=dict(original_id=self.rid,task_id=self.tid,project_id='demo');self.savec(self.c)
        self.archived();self.activate();c=self.current();c['projects']['demo']['history'][oldrid]['project_id']='foreign'
        with self.assertRaisesRegex(ValueError,'history'):self.aa.project_path(self.h,c,'demo')
    def test_adopted_archive_keeps_original_pin_path(self):
        self.archived();self.activate();c=self.current();other=self.h/'ai/other-pins.json';other.write_bytes((self.h/'ai/pins.json').read_bytes());c['structure']['group_ids_allowlist_file']=str(other)
        with self.assertRaisesRegex(ValueError,'pin'):self.aa.project_path(self.h,c,'demo')
    def test_completed_activation_replay_preserves_new_task_state(self):
        v=self.activate();c=self.current();c['projects']['demo']['tasks'][self.tid]['last_completed']=True;self.savec(c)
        before=(self.h/'ai/reminders-sync.json').read_bytes()
        result=self.aa.apply(v['plan'],v['sha256'],True,self.native)
        self.assertEqual(result['phase'],'complete');self.assertEqual((self.h/'ai/reminders-sync.json').read_bytes(),before)
    def test_activation_rejects_incomplete_snapshot(self):
        aa=helper();call=self.native.call
        def incomplete(tool,args):
            data=call(tool,args)
            if tool=='find_reminders':data['has_more']=True
            return data
        self.native.call=incomplete
        with self.assertRaisesRegex(ValueError,'incomplete'):aa.preview(self.h,'Главная копия в приложении.',self.native)

# Не дублировать унаследованные тесты в этом модуле.
for name in list(ArchiveTests.__dict__):
    if name.startswith('test_') and name not in ArchiveAuthorityTests.__dict__:
        setattr(ArchiveAuthorityTests,name,None)
if __name__=='__main__':unittest.main()
