"""All inputs are generated in tmp_path; never copy repository image manifests."""
import hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
FX=ROOT/'tests/fixtures/baseline_diagnostic'
@pytest.fixture
def isolated(tmp_path):
 target=tmp_path/'diagnostic';target.mkdir()
 def copy(source,destination):
  p=target/destination;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
 for name in ['baseline_diagnostic.py','verification/iterative_result_audit.py','verification/continuation_regression_check.py','src/adversarial_ai/evaluation/continuation.py','src/adversarial_ai/evaluation/iterative_evaluation.py','tests/test_iterative_result_audit.py','tests/test_continuation_regression_check.py','tests/test_continuation_commit_input.py']:
  copy(ROOT/name,name)
 for source,dest in [('synthetic_checks.py','test_synthetic.py'),('review_checks.py','test_review_regression.py'),('api_compatibility.py','tests/test_api_compatibility.py'),('diagnostic_integration.py','tests/test_diagnostic_integration.py'),('independent_boundaries.py','tests/test_independent_boundaries.py'),('frozen_v2/baseline_diagnostic.py','tests/fixtures/frozen_v2/baseline_diagnostic.py'),('frozen_v2/verification/iterative_result_audit.py','tests/fixtures/frozen_v2/verification/iterative_result_audit.py')]:copy(FX/source,dest)
 classes={str(i):f'SyntheticClass{i:02}' for i in range(10)}
 manifest={'data_root':'synthetic/not-real','test_samples':781,'test_files':[{'relative_path':f'SyntheticClass{i%10:02}/fake_{i:04}.png','label':f'SyntheticClass{i%10:02}','sha256':hashlib.sha256(f'synthetic-image-{i}'.encode()).hexdigest()} for i in range(781)],'models':[{'path':'models/cnn_baseline.h5','sha256':'a'*64},{'path':'models/mobilenet_finetuned.h5','sha256':'b'*64}]}
 for base in [target,target/'tests/fixtures/frozen_v2']:
  (base/'configs').mkdir(parents=True)
  for name,data in [('classes.json',classes),('test_manifest.json',manifest)]: (base/'configs'/name).write_text(json.dumps(data)+'\n')
 return target

def run(root,*args):
 p=subprocess.run([sys.executable,'-B',*args],cwd=root,env={**os.environ,'PYTHONPATH':str(root)},text=True,capture_output=True,timeout=90)
 assert p.returncode==0,p.stdout+'\n'+p.stderr
 return p.stdout

def test_all_synthetic_boundaries(isolated):
 assert '82 passed' in run(isolated,'-m','pytest','-q','tests','-p','no:cacheprovider')

def test_original_diagnostic_checks(isolated):
 assert json.loads(run(isolated,'test_synthetic.py'))['synthetic_checks']==17

def test_followup_regression_checks(isolated):
 assert '18 cases PASS' in run(isolated,'test_review_regression.py','--verify')

def test_optimized_continuation_checks(isolated):
 result=json.loads(run(isolated,'-O','verification/continuation_regression_check.py'))
 assert result['passed']==result['total']==33 and result['model_inference'] is False
