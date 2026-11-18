"""Synthetic counterexample only; not a new auditor or model experiment."""
import csv, hashlib, importlib.util, json, pathlib, subprocess, tempfile
BASE='93065482deabd1d7ebe708d5e24b0d3a445775b4'
REPO=pathlib.Path(__file__).resolve().parent
from baseline_diagnostic import diagnose, digest
checks=0
def check(x):
 global checks
 assert x
 checks+=1
def blob(path):
 return (REPO/path).read_bytes()
with tempfile.TemporaryDirectory() as td:
 root=pathlib.Path(td);(root/'configs').mkdir();out=root/'synthetic';out.mkdir()
 for name in ['test_manifest.json','classes.json']:(root/'configs'/name).write_bytes(blob('configs/'+name))
 source=blob('verification/iterative_result_audit.py');(root/'auditor.py').write_bytes(source)
 spec=importlib.util.spec_from_file_location('baseline_audit',root/'auditor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 manifest=json.loads((root/'configs/test_manifest.json').read_text());classes=json.loads((root/'configs/classes.json').read_text());labels={v:int(k) for k,v in classes.items()}
 fields=['relative_path','true_index']+[p+'_pred' for p in m.PIPELINES]+['linf','adaptive_linf']
 r=dict(kind='followup_iterative_evaluation',independent_verification_approval=False,source_commit=BASE,source_dirty=False,manifest_sha256=hashlib.sha256((root/'configs/test_manifest.json').read_bytes()).hexdigest(),classes_sha256=hashlib.sha256((root/'configs/classes.json').read_bytes()).hexdigest(),scope=dict(samples=781,models=['cnn','mobilenet'],epsilons=[0,.01,.03,.05],pipelines=list(m.PIPELINES)),status='RUNNING',conditions=[])
 h=next(x['sha256'] for x in manifest['models'] if 'cnn_baseline' in x['path']);vectors=[]
 for i,epsilon in enumerate([.01,.03]):
  rows=[]
  for j,item in enumerate(manifest['test_files']):
   y=labels[item['relative_path'].split('/')[0]];pred={p:y for p in m.PIPELINES}
   if j==0:pred['clean']=(y+1+i)%10
   rows.append(dict(relative_path=item['relative_path'],true_index=y,**{p+'_pred':v for p,v in pred.items()},linf=0,adaptive_linf=0))
  path=out/f'synthetic_{i}.csv'
  with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
  metrics={}
  for p in m.PIPELINES:
   base='defended_clean' if p in ['transfer_defended','adaptive_defended'] else 'clean'
   den=sum(x[base+'_pred']==x['true_index'] for x in rows);suc=sum(x[base+'_pred']==x['true_index'] and x[p+'_pred']!=x['true_index'] for x in rows)
   metrics[p]=dict(accuracy=sum(x[p+'_pred']==x['true_index'] for x in rows)/781,asr_denominator=den,asr_successes=suc,asr=suc/den if den else None)
  vectors.append([x['clean_pred'] for x in rows]);r['conditions'].append(dict(model='cnn',model_sha256=h,method='gaussian',epsilon=epsilon,samples=781,csv=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),metrics=metrics))
 (out/'run.json').write_text(json.dumps(r));a=m.audit(out,root)
 assert a['checked_conditions']==2 and a['result']=='PARTIAL_OUTPUTS_ONLY'
 assert r['conditions'][0]['metrics']==r['conditions'][1]['metrics']
 assert sum(x!=y for x,y in zip(*vectors))==1


 def snapshot():
  return {str(x.relative_to(out)):x.read_bytes() for x in out.rglob('*') if x.is_file()}
 original=(out/'run.json').read_bytes()
 results=[]
 for bad in [None, [], 'invalid']:
  rr=json.loads(original);rr['settings']=bad;(out/'run.json').write_text(json.dumps(rr));before=snapshot()
  try:
   diagnose(out)
   outcome='NO_ERROR'
  except Exception as e:outcome=type(e).__name__+': '+str(e)
  results.append({'case':'settings_'+repr(bad),'outcome':outcome,'unchanged':snapshot()==before})
 for key in ['resume_from','parent_run','continuation']:
  for value in (['synthetic-parent',None,'',False] if key=='resume_from' else ['synthetic-parent',None]):
   rr=json.loads(original);rr['settings']={key:value};(out/'run.json').write_text(json.dumps(rr));before=snapshot()
   try:outcome=diagnose(out,dict(report_sha256=digest((out/'run.json').read_bytes()),execution_id='synthetic-only',environment_sha256='a'*64,settings_sha256='b'*64))['status']
   except Exception as e:outcome=type(e).__name__+': '+str(e)
   results.append({'case':'nested_'+key+'_'+repr(value),'outcome':outcome,'unchanged':snapshot()==before})
 for key in ['resume_from','parent_run','continuation']:
  rr=json.loads(original);rr[key]=None;(out/'run.json').write_text(json.dumps(rr));before=snapshot()
  results.append({'case':'top_'+key,'outcome':diagnose(out)['status'],'unchanged':snapshot()==before})
 (out/'run.json').write_bytes(original);(out/'parent-run.json').write_text('{}');before=snapshot()
 results.append({'case':'parent_file','outcome':diagnose(out)['status'],'unchanged':snapshot()==before})
 (out/'parent-run.json').unlink()
 (out/'run.json').write_bytes(original)
 provenance=dict(report_sha256=digest(original),execution_id='synthetic-only',environment_sha256='a'*64,settings_sha256='b'*64)
 before=snapshot();d=diagnose(out,provenance)
 results.append({'case':'success_immutable','outcome':d['status'],'unchanged':snapshot()==before,'auditor_sha256':d.get('auditor_sha256')})
 csvpath=out/'synthetic_0.csv';csvpath.write_bytes(csvpath.read_bytes()+b'bad');before=snapshot()
 try:diagnose(out,provenance);outcome='NO_ERROR'
 except Exception as e:outcome=type(e).__name__+': '+str(e)
 results.append({'case':'failure_immutable','outcome':outcome,'unchanged':snapshot()==before})
 import shutil,sys
 tamper=root/'tamper';shutil.copytree(REPO,tamper,ignore=shutil.ignore_patterns('__pycache__'))
 auditfile=tamper/'verification/iterative_result_audit.py'
 auditfile.write_text(auditfile.read_text()+"\nraise RuntimeError('TAMPER_EXECUTED')\n")
 proc=subprocess.run([sys.executable,'-B','-c','import baseline_diagnostic'],cwd=tamper,text=True,capture_output=True)
 results.append({'case':'auditor_tamper','returncode':proc.returncode,'outcome':proc.stderr.strip().splitlines()[-1]})
 print(json.dumps(results,indent=2))

if '--verify' in sys.argv:
 assert all(r['unchanged'] for r in results if 'unchanged' in r)
 assert all(r['outcome']=='ValueError: settings must be an object' for r in results if r['case'].startswith('settings_'))
 assert next(r for r in results if r['case']=='nested_resume_from_None')['outcome']=='DIAGNOSTIC_ONLY'
 assert all(r['outcome']=='NOT_COMPARABLE' for r in results if (r['case'].startswith('nested_') and r['case']!='nested_resume_from_None') or r['case'].startswith('top_') or r['case']=='parent_file')
 assert results[-3]['outcome']=='DIAGNOSTIC_ONLY' and results[-3]['auditor_sha256']=='c7f906a7f47c8671cebe5252f6e9b593a6a714b1bb3d68ecc56c866e313b6ed0'
 assert results[-2]['outcome']=='ValueError: CSV hash mismatch'
 assert results[-1]['outcome']=='ValueError: pinned auditor hash mismatch'
 print('REVIEW_REGRESSION: 18 cases PASS (overlapping existing controls; not additive coverage)')
