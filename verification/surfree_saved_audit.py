"""Audit saved SurFree records; not an independent neural-network replay."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from adversarial_ai.evaluation.integrity import sha256_file
from adversarial_ai.evaluation.surfree_evaluation import summarize
from adversarial_ai.attacks.surfree_adapter import UPSTREAM_COMMIT,HASHES


def audit(folder):
    report=json.loads((folder/'run.json').read_text())
    assert report['status'] in ('COMPLETED_PILOT','COMPLETED_NOT_INDEPENDENT_APPROVAL')
    assert report['settings']['model_role'] in ('original','trained')
    assert report['independent_verification_approval'] is False
    assert report['upstream_commit']==UPSTREAM_COMMIT and report['upstream_file_sha256']==HASHES
    manifest=ROOT/'configs/test_manifest.json';classes=ROOT/'configs/classes.json'
    assert report['manifest_sha256']==sha256_file(manifest)
    assert report['classes_sha256']==sha256_file(classes)
    data=json.loads(manifest.read_text());names=list(json.loads(classes.read_text()).values())
    if report['settings']['model_role']=='trained':
        training=ROOT/'results/extensions/cnn_adversarial_20261002/training.json'
        assert report['training_record_sha256']==sha256_file(training)
        assert report['model_sha256']==json.loads(training.read_text())['trained_model_sha256']
    else:assert report['model_sha256']==data['models'][0]['sha256']
    selected=[]
    n=report['settings']['per_class']
    for name in names:
        group=[r for r in data['test_files'] if r['label']==name]
        selected.extend(group[:n] if n else group)
    file=folder/'samples.jsonl';assert sha256_file(file)==report['samples_sha256']
    rows=[json.loads(line) for line in file.read_text().splitlines()]
    assert len(rows)==len(selected)==report['completed_samples']
    for r,m in zip(rows,selected):
        assert r['relative_path']==m['relative_path'] and r['image_sha256']==m['sha256']
        assert names[r['true_index']]==m['label']
        assert 0<=r['clean_pred']<10 and 0<=r['attacked_pred']<10
        assert 1<=r['queries']<=report['settings']['max_queries']
        assert 0<=r['initialization_queries']<=min(200,report['settings']['max_queries']-1)
        assert all(np.isfinite(r[k]) and r[k]>=0 for k in ('l2','linf','rms'))
        assert r['linf']<=1 and r['rms']<=r['linf']+1e-6 and r['linf']<=r['l2']+1e-6
        assert np.isclose(r['rms'],r['l2']/np.sqrt(128*128*3),rtol=1e-5,atol=1e-7)
        assert r['successful']==(r['clean_pred']==r['true_index'] and r['attacked_pred']!=r['true_index'])
        assert r['stop_reason'] in ('clean_misclassified','initialization_failed','query_budget_reached','upstream_finished')
        if r['stop_reason']=='query_budget_reached':assert r['queries']==report['settings']['max_queries']
        if r['clean_pred']!=r['true_index']:
            assert r['queries']==1 and r['l2']==0 and r['stop_reason']=='clean_misclassified'
        elif r['successful']:
            assert 2<=r['first_success_query']<=r['queries'] and r['l2']>0
            assert r['first_success_query']==r['initialization_queries']+1
            assert r['stop_reason'] in ('query_budget_reached','upstream_finished')
        else:
            assert r['l2']==0 and r['first_success_query'] is None
            assert r['stop_reason']=='initialization_failed' and r['attacked_pred']==r['clean_pred']
            assert r['queries']==r['initialization_queries']+1==min(201,report['settings']['max_queries'])
        for q,d in r['best_l2_by_total_queries'].items():
            assert int(q) in (200,1000) and int(q)<=r['queries']
            if d is not None:assert np.isfinite(d) and d>=r['l2']-1e-6
    assert report['metrics']==summarize(rows)
    return len(rows)


if __name__=='__main__':
    folders=[Path(p) for p in sys.argv[1:]] or sorted(p.parent for p in (ROOT/'results/extensions/surfree').glob('*/run.json'))
    for folder in folders:print(f'{folder.name}: PASS ({audit(folder)} rows; saved evidence only)')
