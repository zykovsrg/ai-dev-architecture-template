from pathlib import Path
import tempfile,shutil,subprocess,os,json
root=Path(__file__).resolve().parents[2]
source=root/'modules/planning/scripts';tests=root/'modules/planning/tests'
text=(source/'reminders_external_retirement.py').read_text()
cases=[
('test_large_plan_apply_and_receipt_preserve_exact_history',"    payload = cancel.encoded(plan).encode('utf-8')\n    if len(payload)","    return bounded_payload(plan)\n    payload = cancel.encoded(plan).encode('utf-8')\n    if len(payload)"),
('test_decompression_limit_rejects_bomb','PACKED_LIMIT = 16_777_216','PACKED_LIMIT = 33_554_432'),
('test_invalid_or_trailing_compressed_payload_rejected','if not decoder.eof or decoder.unused_data:','if False:'),
('test_packed_plan_rejects_ambiguous_plain_fields',"'config_raw' in plan or 'projects' in plan or", "'config_raw' in plan or"),
('test_oversize_expansion_leaves_no_journal','if len(raw) > PACKED_LIMIT:\n        raise', 'if False:\n        raise'),
('test_large_plan_resume_after_canonical_write',"allowed=[plan['config'],changed_config(plan,digest),changed_config(plan,digest,True)]", "allowed=[plan['config'],changed_config(plan,digest,True),changed_config(plan,digest,True)]"),
('test_large_plan_exact_config_cas_is_preserved','or raw not in raw_allowed or','or False or'),
('v2:test_oversize_preview_leaves_no_active_journal','return bounded_payload(packed)',"return cancel.encoded(packed).encode('utf-8')")]
results=[]
with tempfile.TemporaryDirectory() as d:
 target=Path(d).resolve()/'scripts';shutil.copytree(source,target,ignore=shutil.ignore_patterns('__pycache__'))
 for name,old,new in cases:
  assert old in text,(name,old)
  (target/'reminders_external_retirement.py').write_text(text.replace(old,new,1))
  test=('test_reminders_external_retirement_plan_v2.PlanV2Tests.'+name[3:] if name.startswith('v2:') else 'test_reminders_external_retirement_plan_size.PlanSizeTests.'+name)
  env=dict(os.environ,EXTERNAL_RETIREMENT_SOURCE=str(target/'reminders_external_retirement.py'),PYTHONDONTWRITEBYTECODE='1')
  r=subprocess.run(['python3','-m','unittest',test],cwd=tests,env=env,capture_output=True,text=True)
  valid=r.returncode!=0 and ('AssertionError' in r.stderr or 'ValueError' in r.stderr) and not any(x in r.stderr for x in ('SyntaxError','ImportError','ModuleNotFoundError','unsafe_path','noncanonical_path'))
  results.append(dict(test=name,mutation=old,rejected=valid,returncode=r.returncode,output=r.stderr[-2200:]))
  print(name,valid,flush=True)
  if not valid:print(r.stderr[:2000],flush=True)
 (target/'reminders_external_retirement.py').write_text(text)
 env=dict(os.environ,EXTERNAL_RETIREMENT_SOURCE=str(target/'reminders_external_retirement.py'),PYTHONDONTWRITEBYTECODE='1')
 for name,_,_ in cases:
  test=('test_reminders_external_retirement_plan_v2.PlanV2Tests.'+name[3:] if name.startswith('v2:') else 'test_reminders_external_retirement_plan_size.PlanSizeTests.'+name)
  r=subprocess.run(['python3','-m','unittest',test],cwd=tests,env=env,capture_output=True,text=True)
  results[cases.index(next(x for x in cases if x[0]==name))]['restored_pass']=r.returncode==0
  if r.returncode:print('RESTORE',name,r.stderr[:1800],flush=True)
(root/'experiments/reminders-plan-size-20261101/mutations.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
assert all(x['rejected'] and x['restored_pass'] for x in results)
