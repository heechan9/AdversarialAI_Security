"""Recalculate saved Square pilot CSV metrics (not an independent model run)."""
import csv
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from adversarial_ai.evaluation.integrity import sha256_file
from adversarial_ai.evaluation.square_evaluation import summarize


def audit(folder):
    report=json.loads((folder/'run.json').read_text())
    assert report['status'] in ('COMPLETED_PILOT','COMPLETED_NOT_INDEPENDENT_APPROVAL')
    assert report['independent_verification_approval'] is False
    manifest=ROOT/'configs/test_manifest.json'
    assert sha256_file(manifest)==report['manifest_sha256']
    assert sha256_file(ROOT/'configs/classes.json')==report['classes_sha256']
    data=json.loads(manifest.read_text())
    assert report['model_sha256'] in [m['sha256'] for m in data['models']]
    classes=json.loads((ROOT/'configs/classes.json').read_text())
    selected=[]
    n=report['settings']['per_class']
    for name in classes.values():
        group=[r for r in data['test_files'] if r['label']==name]
        selected.extend(group[:n] if n else group)
    assert len(report['conditions'])==len(report['settings']['epsilons'])
    clean=None
    for condition,eps in zip(report['conditions'],report['settings']['epsilons']):
        assert condition['epsilon']==eps
        assert Path(condition['csv']).name==condition['csv']
        file=folder/condition['csv']
        assert sha256_file(file)==condition['sha256']
        rows=list(csv.DictReader(file.open()))
        assert len(rows)==len(selected)
        for row,record in zip(rows,selected):
            for key in ('true_index','clean_pred','attacked_pred','queries'):
                row[key]=int(row[key])
            for key in ('linf','final_margin'):
                row[key]=float(row[key]);assert np.isfinite(row[key])
            assert row['relative_path']==record['relative_path']
            assert row['image_sha256']==record['sha256']
            assert classes[str(row['true_index'])]==record['label']
            assert 0<=row['clean_pred']<10 and 0<=row['attacked_pred']<10
            assert 1<=row['queries']<=report['settings']['max_queries']
            assert 0<=row['linf']<=eps+1e-6
            if row['clean_pred']!=row['true_index'] or eps==0:
                assert row['linf']==0 and row['queries']==1
                assert row['attacked_pred']==row['clean_pred']
        predictions=[r['clean_pred'] for r in rows]
        assert clean is None or clean==predictions
        clean=predictions
        assert summarize(rows,report['settings']['max_queries'])==condition['metrics']
    return len(selected)*len(report['conditions'])


if __name__=='__main__':
    folders=[Path(p) for p in sys.argv[1:]] or sorted((ROOT/'results/extensions/square').glob('*pilot_20261003'))
    for folder in folders:
        print(f'{folder.name}: PASS ({audit(folder)} rows; saved evidence only)')
