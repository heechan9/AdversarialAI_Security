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

 provenance=dict(report_sha256=digest((out/'run.json').read_bytes()),execution_id='synthetic-only',environment_sha256='a'*64,settings_sha256='b'*64)
 before={str(x.relative_to(out)):x.read_bytes() for x in out.rglob('*') if x.is_file()}
 d=diagnose(out,provenance)
 after={str(x.relative_to(out)):x.read_bytes() for x in out.rglob('*') if x.is_file()}
 assert before==after
 check(d['status']=='DIAGNOSTIC_ONLY')
 clean=next(g for g in d['groups'] if g['pipeline']=='clean')
 check(clean['status']=='MISMATCH' and clean['changed_unique_images']==clean['changed_comparison_cells']==1)
 check(next(g for g in d['groups'] if g['pipeline']=='defended_clean')['status']=='MATCHED_OBSERVED_BASELINE_LABELS')
 check(d['cause']=='UNKNOWN' and d['independent_verification_approval'] is False)
 check(diagnose(out)['status']=='INSUFFICIENT_PROVENANCE')
 check(diagnose(out,{**provenance,'report_sha256':'bad'})['status']=='INSUFFICIENT_PROVENANCE')
 original=(out/'run.json').read_bytes()
 r0=json.loads(original);r0['settings']={'resume_from':'/prior-run'}
 (out/'run.json').write_text(json.dumps(r0))
 check(diagnose(out,provenance)['reason']=='continuation excluded')
 r0=json.loads(original)
 r0['conditions'][1]['method']='mean'
 (out/'run.json').write_text(json.dumps(r0));p={**provenance,'report_sha256':digest((out/'run.json').read_bytes())}
 groups=diagnose(out,p)['groups']
 check(len(groups)==3 and all(g['status']=='NOT_COMPARABLE' for g in groups if g['pipeline']=='defended_clean'))
 r0=json.loads(original);r0['conditions'][1].update(csv=r0['conditions'][0]['csv'],sha256=r0['conditions'][0]['sha256'],metrics=r0['conditions'][0]['metrics'])
 (out/'run.json').write_text(json.dumps(r0));p={**provenance,'report_sha256':digest((out/'run.json').read_bytes())}
 check(all(g['status']=='NOT_COMPARABLE' and g['duplicate_content_conditions']==1 for g in diagnose(out,p)['groups']))
 r0=json.loads(original);r0['conditions']=[]
 (out/'run.json').write_text(json.dumps(r0));p={**provenance,'report_sha256':digest((out/'run.json').read_bytes())}
 check(diagnose(out,p)['groups']==[])
 (out/'run.json').write_bytes(original)

 r['conditions'].reverse();(out/'run.json').write_text(json.dumps(r))
 p={**provenance,'report_sha256':digest((out/'run.json').read_bytes())}
 check(diagnose(out,p)['groups']==d['groups'])
 r['conditions']=r['conditions'][:1];(out/'run.json').write_text(json.dumps(r))
 p={**provenance,'report_sha256':digest((out/'run.json').read_bytes())}
 check(all(g['status']=='NOT_COMPARABLE' for g in diagnose(out,p)['groups']))
 r['continuation']={'parent_report_sha256':'a'*64};(out/'run.json').write_text(json.dumps(r))
 check(diagnose(out,provenance)['reason']=='continuation excluded')
 (out/'run.json').write_bytes(original)
 first=out/'synthetic_0.csv';content=first.read_bytes();first.write_bytes(content+b'bad')
 try:diagnose(out,provenance);raise AssertionError('hash accepted')
 except ValueError:checks+=1
 first.unlink();first.symlink_to(out/'synthetic_1.csv')
 try:diagnose(out,provenance);raise AssertionError('symlink accepted')
 except OSError:checks+=1
 first.unlink();first.write_bytes(content)
 (out/'run.json').write_text('{"kind":1,"kind":2}')
 try:diagnose(out,provenance);raise AssertionError('duplicate key accepted')
 except ValueError:checks+=1
 (out/'run.json').write_bytes(original)
 check(before==after)
 print(json.dumps(dict(synthetic_checks=checks,real_experiments=0,external_reviews=0)))
