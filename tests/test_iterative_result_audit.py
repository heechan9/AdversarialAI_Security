import csv,hashlib,itertools,json
from pathlib import Path
import pytest
from verification.iterative_result_audit import audit

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def case(tmp_path):
    manifest=json.loads((ROOT/'configs/test_manifest.json').read_text())
    classes=json.loads((ROOT/'configs/classes.json').read_text());index={v:int(k) for k,v in classes.items()}
    fields=['relative_path','true_index']+[k+'_pred' for k in ('clean','defended_clean','attacked','transfer_defended','adaptive_defended')]+['linf','adaptive_linf']
    f=tmp_path/'samples.csv'
    with f.open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=fields);w.writeheader()
        for row in manifest['test_files']:
            true=index[row['relative_path'].split('/')[0]]
            w.writerow(dict(relative_path=row['relative_path'],true_index=true,**{k:true for k in fields if k.endswith('_pred')},linf=0,adaptive_linf=0))
    metrics={k:dict(accuracy=1.,asr=0.,asr_successes=0,asr_denominator=781) for k in ('clean','defended_clean','attacked','transfer_defended','adaptive_defended')}
    report=dict(kind='followup_iterative_evaluation',independent_verification_approval=False,source_commit='a'*40,source_dirty=False,
      manifest_sha256=hashlib.sha256((ROOT/'configs/test_manifest.json').read_bytes()).hexdigest(),classes_sha256=hashlib.sha256((ROOT/'configs/classes.json').read_bytes()).hexdigest(),
      scope=dict(samples=781,models=['cnn','mobilenet'],epsilons=[0,.01,.03,.05],pipelines=list(metrics)),status='RUNNING',conditions=[])
    hashes={('cnn' if 'cnn_baseline' in x['path'] else 'mobilenet'):x['sha256'] for x in manifest['models']}
    for model,method,epsilon in itertools.product(['cnn','mobilenet'],['gaussian','mean'],[0,.01,.03,.05]):
        report['conditions'].append(dict(model=model,method=method,epsilon=epsilon,model_sha256=hashes[model],csv='samples.csv',sha256=hashlib.sha256(f.read_bytes()).hexdigest(),samples=781,metrics=metrics))
    return tmp_path,report

def check(case):
    folder,report=case;(folder/'run.json').write_text(json.dumps(report));return audit(folder,ROOT)

def test_complete_and_partial_are_distinct(case):
    folder,r=case
    assert check(case)['result']=='PARTIAL_OUTPUTS_ONLY'
    r['status']='COMPLETED_NOT_INDEPENDENT_APPROVAL'
    assert check(case)['result']=='FULL_OUTPUTS_CONSISTENT'
    r['conditions'].pop()
    with pytest.raises(ValueError,match='missing conditions'):check(case)

@pytest.mark.parametrize('change',[
 lambda r:r.update(independent_verification_approval=True),lambda r:r.update(source_dirty=True),
 lambda r:r['conditions'][0].update(sha256='0'*64),lambda r:r['conditions'][0].update(samples=780),
 lambda r:r['conditions'][0].update(csv='../samples.csv'),lambda r:r['conditions'].append(r['conditions'][0]),
 lambda r:r['conditions'][0]['metrics']['clean'].update(accuracy=.9),
 lambda r:r['conditions'][0]['metrics']['clean'].update(asr_denominator=780),
 lambda r:r['scope'].update(models=['cnn']),lambda r:r.update(manifest_sha256='0'*64)])
def test_corruption_rejected(case,change):
    change(case[1])
    with pytest.raises(ValueError):check(case)
