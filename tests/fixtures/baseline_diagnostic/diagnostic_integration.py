"""Integration boundaries, no model calls or real outputs."""
import hashlib,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
import pytest
from test_iterative_result_audit import case
import baseline_diagnostic as integrated
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'tests/fixtures/frozen_v2/baseline_diagnostic.py'
spec=importlib.util.spec_from_file_location('frozen_v2',OLD)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
def test_diagnostic_output_only_auditor_metadata_differs(case):
 folder,r=case;r['settings']={'resume_from':None};b=json.dumps(r).encode();(folder/'run.json').write_bytes(b)
 p=dict(report_sha256=hashlib.sha256(b).hexdigest(),execution_id='synthetic',environment_sha256='a'*64,settings_sha256='b'*64)
 a=old.diagnose(folder,p);z=integrated.diagnose(folder,p)
 assert a.pop('auditor_sha256')!=z.pop('auditor_sha256')
 assert a==z
@pytest.mark.parametrize('where,key',[('root',k) for k in ['resume_from','parent_run','continuation']]+[('settings',k) for k in ['parent_run','continuation','resume_from']]+[('file','parent-run.json')])
def test_continuation_excluded_before_audit(case,monkeypatch,where,key):
 folder,r=case
 if where=='root':r[key]=None
 elif where=='settings':r['settings']={key:'synthetic' if key=='resume_from' else None}
 else:(folder/key).write_text('{}')
 (folder/'run.json').write_text(json.dumps(r))
 def forbidden(*a,**k):raise AssertionError('auditor must not run for excluded continuation')
 monkeypatch.setattr(integrated.audit_module,'audit',forbidden)
 assert integrated.diagnose(folder)['status']=='NOT_COMPARABLE'
@pytest.mark.parametrize('mode',['old_main','tamper'])
def test_wrong_auditor_rejected_before_execution(tmp_path,mode):
 shutil.copy(ROOT/'baseline_diagnostic.py',tmp_path/'baseline_diagnostic.py');(tmp_path/'verification').mkdir()
 b=(ROOT/'tests/fixtures/frozen_v2/verification/iterative_result_audit.py').read_bytes() if mode=='old_main' else (ROOT/'verification/iterative_result_audit.py').read_bytes()+b"\nraise RuntimeError('MUST_NOT_EXECUTE')\n"
 (tmp_path/'verification/iterative_result_audit.py').write_bytes(b)
 p=subprocess.run([sys.executable,'-B','-c','import baseline_diagnostic'],cwd=tmp_path,capture_output=True,text=True)
 assert p.returncode!=0 and p.stderr.strip().endswith('ValueError: pinned auditor hash mismatch')
 assert 'RuntimeError: MUST_NOT_EXECUTE' not in p.stderr

@pytest.mark.parametrize('mismatch',[False,True])
def test_distinct_csv_matched_and_mismatched_equivalence(case,mismatch):
 import csv,copy
 folder,r=case
 r['conditions']=[copy.deepcopy(c) for c in r['conditions'] if c['model']=='cnn' and c['method']=='gaussian' and c['epsilon'] in (.01,.03)]
 for i,c in enumerate(r['conditions']):
  with (folder/'samples.csv').open(newline='') as f:rows=list(csv.DictReader(f));fields=list(rows[0])
  if i:
   rows[0]['linf']='0.001' # Distinct bytes even when all clean labels match.
   if mismatch:rows[0]['clean_pred']=str((int(rows[0]['true_index'])+1)%10)
  name=f'distinct_{i}.csv'
  with (folder/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
  c['csv']=name;c['sha256']=hashlib.sha256((folder/name).read_bytes()).hexdigest()
  for pipeline in integrated.audit_module.PIPELINES:
   base='defended_clean' if pipeline in ('transfer_defended','adaptive_defended') else 'clean'
   den=sum(x[base+'_pred']==x['true_index'] for x in rows)
   num=sum(x[base+'_pred']==x['true_index'] and x[pipeline+'_pred']!=x['true_index'] for x in rows)
   c['metrics'][pipeline]=dict(accuracy=sum(x[pipeline+'_pred']==x['true_index'] for x in rows)/781,asr_denominator=den,asr_successes=num,asr=num/den if den else None)
 r['settings']={'resume_from':None};b=json.dumps(r).encode();(folder/'run.json').write_bytes(b)
 p=dict(report_sha256=hashlib.sha256(b).hexdigest(),execution_id='synthetic',environment_sha256='a'*64,settings_sha256='b'*64)
 before={x.name:x.read_bytes() for x in folder.iterdir()}
 a=old.diagnose(folder,p);z=integrated.diagnose(folder,p)
 a.pop('auditor_sha256');z.pop('auditor_sha256');assert a==z
 clean=next(g for g in z['groups'] if g['pipeline']=='clean')
 assert clean['distinct_csv_contents']==2
 assert clean['status']==('MISMATCH' if mismatch else 'MATCHED_OBSERVED_BASELINE_LABELS')
 assert before=={x.name:x.read_bytes() for x in folder.iterdir()}
