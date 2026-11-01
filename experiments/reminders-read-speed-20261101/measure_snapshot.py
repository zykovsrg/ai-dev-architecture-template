"""Чтение приложения и сравнение методов на одинаковых записанных ответах. Личные ответы — только во временный файл."""
import collections,copy,importlib.util,json,sys,time
from pathlib import Path
import argparse
parser=argparse.ArgumentParser()
parser.add_argument('--hub',required=True,type=Path)
parser.add_argument('--raw-output',required=True,type=Path)
args=parser.parse_args()
hub=args.hub.resolve()
root=hub/'projects/ai-dev-architecture'
sys.path.insert(0,str(hub/'scripts'))
import reminders_sync as installed
config=installed.load_config(hub)
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
new=load('measure_batch_structure',root/'modules/planning/scripts/reminders_structure.py')
old=load('measure_old_structure',root/'experiments/reminders-read-speed-20261101/structure-before.py')
allow=json.loads(Path(new.standard_allowlist(config)).read_text());names=set(allow.get('names',[]) if isinstance(allow,dict) else allow)
roles=config['structure']['list_roles']
class Recording:
 def __init__(self):self.native=new.StructureNative(config);self.records=[]
 def call(self,tool,args):
  start=time.monotonic();value=self.native.call(tool,args)
  self.records.append(dict(tool=tool,args=copy.deepcopy(args),value=copy.deepcopy(value),seconds=time.monotonic()-start))
  return value
native=Recording();start=time.monotonic()
try:
 with installed.reads_module().run_scope():actual=new.snapshot(native,roles,names,detailed=True,include_groups=True)
except Exception:
 args.raw_output.write_text(json.dumps(native.records,ensure_ascii=False))
 raise
elapsed=time.monotonic()-start
args.raw_output.write_text(json.dumps(native.records,ensure_ascii=False))
class Replay:
 def __init__(self):self.calls=[]
 def call(self,tool,args):
  self.calls.append((tool,args))
  if tool=='get_reminder':return copy.deepcopy(actual['reminders'][args['id']])
  return copy.deepcopy(next(row['value'] for row in native.records if row['tool']==tool and row['args']==args))
a,b=Replay(),Replay();before=old.snapshot(a,roles,names,detailed=True,include_groups=True);after=new.snapshot(b,roles,names,detailed=True,include_groups=True)
counts=lambda calls:dict(collections.Counter(tool+(':detail' if args.get('detail') else '') for tool,args in calls))
result=dict(ok=before==after==actual,lists=len(actual['lists']),reminders=len(actual['reminders']),live_snapshot_seconds=elapsed,
 old_replay_calls=counts(a.calls),new_replay_calls=counts(b.calls),live_calls=counts([(r['tool'],r['args']) for r in native.records]),
 live_time_by_tool={tool:sum(r['seconds'] for r in native.records if r['tool']==tool) for tool in {r['tool'] for r in native.records}})
(root/'experiments/reminders-read-speed-20261101/snapshot-measurement.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(0 if result['ok'] else 1)
