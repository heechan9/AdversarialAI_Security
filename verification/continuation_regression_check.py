import csv, hashlib, itertools, json, tempfile, importlib.util, sys, shutil, subprocess, copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
version='working-tree'
spec=importlib.util.spec_from_file_location('verification.iterative_result_audit',ROOT/'verification/iterative_result_audit.py'); auditmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditmod)
# Use the real CSV audit implementation, not a stub.
import types
pkg=types.ModuleType('verification');sys.modules['verification']=pkg;sys.modules['verification.iterative_result_audit']=auditmod
spec=importlib.util.spec_from_file_location('continuation',ROOT/'src/adversarial_ai/evaluation/continuation.py'); cont=importlib.util.module_from_spec(spec);spec.loader.exec_module(cont)
P=auditmod.PIPELINES
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def record(name,actual,expected):
 checks.append(dict(name=name,actual=actual,expected=expected,pass_=actual==expected))
def create(folder,root):
 folder.mkdir()
 manifest=json.loads((root/'configs/test_manifest.json').read_text());classes=json.loads((root/'configs/classes.json').read_text());labels={v:int(k) for k,v in classes.items()}
 csvfile=folder/'samples.csv';fields=['relative_path','true_index']+[p+'_pred' for p in P]+['linf','adaptive_linf']
 with csvfile.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for entry in manifest['test_files']:
   label=labels[entry['relative_path'].split('/')[0]];w.writerow(dict(relative_path=entry['relative_path'],true_index=label,**{p+'_pred':label for p in P},linf=0,adaptive_linf=0))
 hashes={('cnn' if 'cnn_baseline' in x['path'] else 'mobilenet'):x['sha256'] for x in manifest['models']}
 r=dict(kind='followup_iterative_evaluation',independent_verification_approval=False,source_commit='a'*40,source_dirty=False,manifest_sha256=sha(root/'configs/test_manifest.json'),classes_sha256=sha(root/'configs/classes.json'),scope=dict(samples=781,models=['cnn','mobilenet'],epsilons=[0,.01,.03,.05],pipelines=list(P)),status='COMPLETED_NOT_INDEPENDENT_APPROVAL',conditions=[],settings={k:1 for k in ('attack','steps','step_size','restarts','seed','batch_size')},**{k:'synthetic-fixed' for k in ('python','platform','tensorflow','keras','numpy','environment')})
 for model,method,epsilon in itertools.product(['cnn','mobilenet'],['gaussian','mean'],[0,.01,.03,.05]):
  r['conditions'].append(dict(model=model,method=method,epsilon=epsilon,model_sha256=hashes[model],csv='samples.csv',sha256=sha(csvfile),samples=781,metrics={p:dict(accuracy=1.,asr=0.,asr_successes=0,asr_denominator=781) for p in P}))
 return r
def save(folder,r): (folder/'run.json').write_text(json.dumps(r))
def result(folder,root):
 try:return auditmod.audit(folder,root)['result']
 except (ValueError,KeyError) as e:return 'REJECTED'
with tempfile.TemporaryDirectory() as d:
 d=Path(d);folder=d/'run';r=create(folder,ROOT);save(folder,r)
 record('plain_complete',result(folder,ROOT),'FULL_OUTPUTS_CONSISTENT')
 parent=copy.deepcopy(r)
 for key in ('none','manifest_sha256','classes_sha256','scope','settings','python','platform','tensorflow','keras','numpy','environment','kind','source_dirty','independent_verification_approval'):
  pp=copy.deepcopy(parent)
  if key!='none':pp[key]=True if key in ('source_dirty','independent_verification_approval') else ({'seed':999} if key=='settings' else 'mismatch')
  (folder/'parent-run.json').write_text(json.dumps(pp));child=copy.deepcopy(r);child['continuation']=dict(parent_report_sha256=sha(folder/'parent-run.json'),parent_source_commit=pp['source_commit'],inherited_conditions=16);save(folder,child)
  record('lineage_'+key,result(folder,ROOT),'FULL_OUTPUTS_CONSISTENT' if key=='none' else 'REJECTED')
 for key in ('attack','steps','step_size','restarts','seed','batch_size'):
  pp=copy.deepcopy(r);pp['settings'][key]=999
  (folder/'parent-run.json').write_text(json.dumps(pp));child=copy.deepcopy(r);child['continuation']=dict(parent_report_sha256=sha(folder/'parent-run.json'),parent_source_commit=pp['source_commit'],inherited_conditions=16);save(folder,child)
  record('lineage_protocol_'+key,result(folder,ROOT),'REJECTED')
 # Legitimate per-run bookkeeping may change without changing protocol.
 parent=copy.deepcopy(r);parent['settings'].update(run_id='old',resume_from=None,data_dir='/old')
 child=copy.deepcopy(r);child['settings'].update(run_id='new',resume_from='/old/run',data_dir='/new')
 (folder/'parent-run.json').write_text(json.dumps(parent));child['continuation']=dict(parent_report_sha256=sha(folder/'parent-run.json'),parent_source_commit=parent['source_commit'],inherited_conditions=16);save(folder,child)
 record('lineage_bookkeeping_allowed',result(folder,ROOT),'FULL_OUTPUTS_CONSISTENT')
 # Real git source guard, audited synthetic 781-row CSVs, no model calls.
 repo=d/'repo';repo.mkdir();shutil.copytree(ROOT/'configs',repo/'configs');runner=repo/'src/adversarial_ai/evaluation/iterative_evaluation.py';runner.parent.mkdir(parents=True);runner.write_text('seed = 1\n')
 def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
 git('init','-q');git('config','user.email','test@example.invalid');git('config','user.name','Synthetic');git('add','.');git('commit','-qm','base');old=git('rev-parse','HEAD')
 source=d/'source';parent=create(source,repo);parent['source_commit']=old;save(source,parent)
 for mode in ('unchanged','csv_exists','parent_exists','dangling_symlink','runner_change'):
  out=d/mode;out.mkdir();child=copy.deepcopy(parent);before={}
  if mode in ('csv_exists','parent_exists'):
   name='samples.csv' if mode=='csv_exists' else 'parent-run.json';(out/name).write_bytes(b'PROTECTED_EXISTING_RESULT');before[name]=(out/name).read_bytes()
  if mode=='dangling_symlink':(out/'samples.csv').symlink_to(out/'nonexistent')
  if mode=='runner_change':
   runner.write_text('seed = 2\n');git('add','.');git('commit','-qm','seed changed');child['source_commit']=git('rev-parse','HEAD')
  try:cont.carry_forward(source,out,child,repo);actual='ACCEPTED'
  except (ValueError,FileExistsError) as e:actual='REJECTED'
  record('carry_'+mode,actual,'ACCEPTED' if mode=='unchanged' else 'REJECTED')
  if before:record('preserved_'+mode,all((out/n).read_bytes()==v for n,v in before.items()),True)
 # Exercise a real CSV audit followed by a concurrent lineage-file writer.
 out=d/'race';out.mkdir();child=copy.deepcopy(parent);real_audit=auditmod.audit
 def racing_audit(*args,**kwargs):
  value=real_audit(*args,**kwargs)
  (out/'parent-run.json').write_bytes(b'concurrent-writer')
  return value
 auditmod.audit=racing_audit
 try:
  try:cont.carry_forward(source,out,child,repo);actual='ACCEPTED'
  except FileExistsError:actual='REJECTED'
 finally:auditmod.audit=real_audit
 record('race_rejected',actual,'REJECTED')
 record('race_existing_parent_preserved',(out/'parent-run.json').read_bytes()==b'concurrent-writer',True)
 record('race_report_not_marked_complete','continuation' not in child,True)
 # Per-file no-clobber is not a transaction: a newly copied CSV can remain.
 record('race_partial_csv_left_documented',(out/'samples.csv').exists(),True)
print(json.dumps({'version':version,'checks':checks,'passed':sum(x['pass_'] for x in checks),'total':len(checks),'synthetic':True,'model_inference':False,'audit_stubbed':False},indent=2))
sys.exit(0 if all(x['pass_'] for x in checks) else 1)
