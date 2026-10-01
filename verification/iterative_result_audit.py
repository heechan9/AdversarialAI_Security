"""Recompute follow-up CSV metrics; partial coverage can never become full PASS."""
import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import re

PIPELINES=('clean','defended_clean','attacked','transfer_defended','adaptive_defended')


def require(ok,message):
    if not ok:raise ValueError(message)


def read_json(path):
    def invalid(value):raise ValueError('nonfinite JSON')
    return json.loads(Path(path).read_text(),parse_constant=invalid)


def audit(run_dir,repo_root):
    run_dir=Path(run_dir);root=Path(repo_root)
    r=read_json(run_dir/'run.json');manifest=read_json(root/'configs/test_manifest.json');classes=read_json(root/'configs/classes.json')
    require(r['kind'] in ('followup_iterative_evaluation','followup_trained_model_iterative_evaluation'),'wrong report kind')
    require(r['independent_verification_approval'] is False,'independent approval prohibited')
    require(re.fullmatch('[0-9a-f]{40}',r['source_commit']) is not None and r['source_dirty'] is False,'uncommitted source')
    require(r['manifest_sha256']==hashlib.sha256((root/'configs/test_manifest.json').read_bytes()).hexdigest(),'manifest hash differs')
    require(r['classes_sha256']==hashlib.sha256((root/'configs/classes.json').read_bytes()).hexdigest(),'class map hash differs')
    expected_paths=[v['relative_path'] for v in manifest['test_files']]
    require(len(expected_paths)==len(set(expected_paths))==manifest['test_samples']==781,'invalid test coverage')
    labels={v:int(k) for k,v in classes.items()}
    require(sorted(labels.values())==list(range(10)),'class map must cover ten classes')
    models=r['scope'].get('models',['cnn','mobilenet'])
    if r['kind']=='followup_iterative_evaluation':require(models==['cnn','mobilenet'],'missing original model scope')
    else:require(models==[r['settings']['trained_model_kind']],'trained model scope mismatch')
    require(r['scope']['samples']==781 and r['scope']['epsilons']==[0,.01,.03,.05] and r['scope']['pipelines']==list(PIPELINES),'scope mismatch')
    expected=set(itertools.product(models,('gaussian','mean'),(0.,.01,.03,.05)))
    seen=set();checked=[]
    original_hash={('cnn' if 'cnn_baseline' in v['path'] else 'mobilenet'):v['sha256'] for v in manifest['models']}
    for condition in r['conditions']:
        key=(condition['model'],condition['method'],condition['epsilon'])
        require(key in expected and key not in seen,'duplicate/unexpected condition');seen.add(key)
        model_hash=original_hash[key[0]] if r['kind']=='followup_iterative_evaluation' else r['trained_model_sha256']
        require(condition['model_sha256']==model_hash,'model identity mismatch')
        name=condition['csv'];require(Path(name).name==name and name.endswith('.csv'),'unsafe CSV name')
        p=run_dir/name;require(not p.is_symlink(),'CSV symlink forbidden')
        require(hashlib.sha256(p.read_bytes()).hexdigest()==condition['sha256'],'CSV hash mismatch')
        with p.open(newline='') as f:rows=list(csv.DictReader(f))
        require(len(rows)==condition['samples']==781,'incomplete condition rows')
        require([v['relative_path'] for v in rows]==expected_paths,'sample order differs')
        for row in rows:
            for field in ('true_index',)+tuple(k+'_pred' for k in PIPELINES):
                require(row[field] in tuple(str(i) for i in range(10)),'invalid class index');row[field]=int(row[field])
            require(row['true_index']==labels[row['relative_path'].split('/')[0]],'wrong true label')
            for field in ('linf','adaptive_linf'):
                value=float(row[field]);require(math.isfinite(value) and 0<=value<=key[2]+1e-6,'invalid perturbation')
            if key[2]==0:
                require(row['clean_pred']==row['attacked_pred'] and row['defended_clean_pred']==row['transfer_defended_pred']==row['adaptive_defended_pred'],'epsilon-zero predictions differ')
        for pipeline in PIPELINES:
            base='defended_clean' if pipeline in ('transfer_defended','adaptive_defended') else 'clean'
            denominator=sum(v[base+'_pred']==v['true_index'] for v in rows)
            successes=sum(v[base+'_pred']==v['true_index'] and v[pipeline+'_pred']!=v['true_index'] for v in rows)
            accuracy=sum(v[pipeline+'_pred']==v['true_index'] for v in rows)/781
            observed=condition['metrics'][pipeline]
            require(observed['asr_denominator']==denominator and observed['asr_successes']==successes,'ASR counts differ')
            require(math.isfinite(observed['accuracy']) and abs(observed['accuracy']-accuracy)<=1e-12,'accuracy differs')
            if denominator:require(observed['asr'] is not None and math.isfinite(observed['asr']) and abs(observed['asr']-successes/denominator)<=1e-12,'ASR differs')
            else:require(observed['asr'] is None,'zero denominator must be null')
        checked.append({'model':key[0],'method':key[1],'epsilon':key[2],'rows':len(rows)})
    if 'continuation' in r:
        lineage=r['continuation'];parent_path=run_dir/'parent-run.json'
        require(not parent_path.is_symlink(),'parent report symlink forbidden')
        require(hashlib.sha256(parent_path.read_bytes()).hexdigest()==lineage['parent_report_sha256'],'parent report hash mismatch')
        parent=read_json(parent_path);n=lineage['inherited_conditions']
        require(type(n) is int and 0<=n<=len(r['conditions']),'invalid inherited count')
        require(parent['source_commit']==lineage['parent_source_commit'],'parent source mismatch')
        require(parent['conditions']==r['conditions'][:n],'inherited conditions differ')
    completed=r['status']=='COMPLETED_NOT_INDEPENDENT_APPROVAL'
    require(r['status'] in ('RUNNING','ERROR','INTERRUPTED','COMPLETED_NOT_INDEPENDENT_APPROVAL'),'unknown run status')
    require(not completed or seen==expected,'completed report missing conditions')
    return dict(kind='followup_csv_recalculation',source_commit=r['source_commit'],
        result='FULL_OUTPUTS_CONSISTENT' if completed else 'PARTIAL_OUTPUTS_ONLY',
        execution_status=r['status'],checked_conditions=len(seen),expected_conditions=len(expected),conditions=checked,
        independent_verification_approval=False,probabilities_compared=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run_dir',type=Path)
    p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args()
    print(json.dumps(audit(a.run_dir,a.repo_root),indent=2))

if __name__=='__main__':main()
