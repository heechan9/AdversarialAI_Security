import copy,hashlib,json,os
import pytest
from test_iterative_result_audit import case
import baseline_diagnostic as d
from verification.iterative_result_audit import audit
ROOT=d.ROOT

def save(folder,r):
 b=json.dumps(r).encode();(folder/'run.json').write_bytes(b)
 return dict(report_sha256=hashlib.sha256(b).hexdigest(),execution_id='synthetic-only',environment_sha256='a'*64,settings_sha256='b'*64)

@pytest.mark.parametrize('leaf',['run.json','samples.csv'])
@pytest.mark.parametrize('kind',['symlink','fifo','directory'])
def test_nonregular_inputs_rejected(case,leaf,kind):
 folder,r=case;p=save(folder,r);target=folder/leaf
 target.unlink()
 if kind=='symlink':target.symlink_to(folder/'absent')
 elif kind=='fifo':os.mkfifo(target)
 else:target.mkdir()
 with pytest.raises((ValueError,OSError)):d.diagnose(folder,p)

@pytest.mark.parametrize('value',[False,'',0,[],{}])
def test_falsey_resume_never_reaches_audit(case,monkeypatch,value):
 folder,r=case;r['settings']={'resume_from':value};p=save(folder,r)
 monkeypatch.setattr(d.audit_module,'audit',lambda *x:pytest.fail('excluded input reached auditor'))
 assert d.diagnose(folder,p)['status']=='NOT_COMPARABLE'

def test_duplicate_csv_read_once_and_frozen(case,monkeypatch):
 folder,r=case;p=save(folder,r);orig=d.read_leaf;seen=[]
 def hooked(fd,name):
  b=orig(fd,name);seen.append(name)
  if name=='samples.csv':(folder/name).write_bytes(b'changed-after-capture')
  return b
 monkeypatch.setattr(d,'read_leaf',hooked)
 z=d.diagnose(folder,p)
 assert seen.count('samples.csv')==1
 assert z['status']=='DIAGNOSTIC_ONLY' and z['per_condition_audit']=='PARTIAL_OUTPUTS_ONLY'
 assert all(g['status']=='NOT_COMPARABLE' for g in z['groups'])
 assert z['independent_verification_approval'] is False

@pytest.mark.parametrize('provenance',[None,{}, {'report_sha256':'0'*64}])
def test_no_attestation_no_comparison(case,provenance):
 folder,r=case;save(folder,r)
 z=d.diagnose(folder,provenance)
 assert z['status']=='INSUFFICIENT_PROVENANCE' and z['groups']==[]

@pytest.mark.parametrize('mutator',[lambda r:r.update(independent_verification_approval=1),lambda r:r.update(source_dirty=0)])
def test_bool_identity_not_numeric_coercion(case,mutator):
 folder,r=case;mutator(r);p=save(folder,r)
 with pytest.raises(ValueError):d.diagnose(folder,p)

@pytest.mark.parametrize('changed',['docs','runner'])
def test_actual_git_source_guard_scope(case,tmp_path,changed):
 import subprocess,shutil,importlib.util
 folder,r=case;repo=folder/'repo';repo.mkdir();shutil.copytree(ROOT/'configs',repo/'configs')
 runner=repo/'src/adversarial_ai/evaluation/iterative_evaluation.py';runner.parent.mkdir(parents=True);runner.write_text('seed = 1\n')
 def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
 git('init','-q');git('config','user.email','synthetic@example.invalid');git('config','user.name','Synthetic only');git('add','.');git('commit','-qm','synthetic base');old=git('rev-parse','HEAD')
 r.update(source_commit=old,settings={k:1 for k in ('attack','steps','step_size','restarts','seed','batch_size')},**{k:'synthetic' for k in ('python','platform','tensorflow','keras','numpy','environment')});save(folder,r)
 if changed=='runner':runner.write_text('seed = 2\n')
 else:(repo/'notes.txt').write_text('synthetic documentation\n')
 git('add','.');git('commit','-qm','synthetic change');child=copy.deepcopy(r);child['source_commit']=git('rev-parse','HEAD')
 out=folder/'out';out.mkdir()
 spec=__import__('importlib.util',fromlist=['x']).spec_from_file_location('independent_cont',ROOT/'src/adversarial_ai/evaluation/continuation.py');m=__import__('importlib.util',fromlist=['x']).module_from_spec(spec);spec.loader.exec_module(m)
 if changed=='runner':
  with pytest.raises(ValueError,match='source differs'):m.carry_forward(folder,out,child,repo)
  assert not list(out.iterdir()) and 'continuation' not in child
 else:
  assert len(m.carry_forward(folder,out,child,repo))==16
  assert child['continuation']['parent_source_commit']==old
  assert (out/'samples.csv').read_bytes()==(folder/'samples.csv').read_bytes()
