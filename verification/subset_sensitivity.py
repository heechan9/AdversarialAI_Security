"""Recalculate saved predictions on predefined exact-duplicate sensitivity subsets.

These are descriptive sensitivity views, not newly independent held-out tests.
The original 781-image results are never replaced.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from verification.iterative_result_audit import audit, PIPELINES, require


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def subsets(manifest, test_manifest):
    paths=[r['relative_path'] for r in test_manifest['test_files']]
    require(len(paths)==len(set(paths))==781,'locked test set required')
    all_paths=set(paths)
    overlap=manifest['source_train_overlap_test_paths']
    require(len(overlap)==len(set(overlap)) and set(overlap)<=all_paths,'invalid overlap membership')
    groups=manifest['test_exact_rgb_duplicate_groups'];seen=set();removed=set()
    for group in groups:
        require(len(group)>1 and len(set(group))==len(group),'invalid duplicate group')
        require(set(group)<=all_paths and not seen.intersection(group),'overlapping/unknown duplicate groups')
        seen.update(group);removed.update(sorted(group)[1:])
        require(not set(group).intersection(overlap) or set(group)<=set(overlap),'overlap must include all identical test copies')
    views={'full_781':all_paths,'source_train_disjoint':all_paths-set(overlap),
           'unique_test_rgb':all_paths-removed,'source_train_disjoint_unique':all_paths-set(overlap)-removed}
    require({k:len(v) for k,v in views.items()}==manifest['subset_counts'],'subset counts mismatch')
    return views


def recalculate(run_dir, subset_path, repo_root):
    root=Path(repo_root);run=Path(run_dir);checked=audit(run,root)
    manifest=json.loads(Path(subset_path).read_text())
    require(manifest['test_manifest_sha256']==sha(root/'configs/test_manifest.json'),'subset test identity differs')
    views=subsets(manifest,json.loads((root/'configs/test_manifest.json').read_text()))
    report=json.loads((run/'run.json').read_text());conditions=[]
    for condition in report['conditions']:
        rows=list(csv.DictReader((run/condition['csv']).open(newline='')))
        result={}
        for view,keep in views.items():
            chosen=[r for r in rows if r['relative_path'] in keep]
            require(len(chosen)==len(keep),'subset row coverage mismatch')
            metrics={}
            for pipeline in PIPELINES:
                base='defended_clean' if pipeline in ('transfer_defended','adaptive_defended') else 'clean'
                correct=sum(r[pipeline+'_pred']==r['true_index'] for r in chosen)
                metric={'correct':correct,'samples':len(chosen),'accuracy':correct/len(chosen)}
                if pipeline in ('attacked','transfer_defended','adaptive_defended'):
                    denominator=sum(r[base+'_pred']==r['true_index'] for r in chosen)
                    success=sum(r[base+'_pred']==r['true_index'] and r[pipeline+'_pred']!=r['true_index'] for r in chosen)
                    metric.update(asr_successes=success,asr_denominator=denominator,asr=success/denominator if denominator else None)
                metrics[pipeline]=metric
            result[view]=metrics
        conditions.append({k:condition[k] for k in ('model','method','epsilon','csv','sha256')}|{'subsets':result})
    return {'kind':'descriptive_subset_sensitivity','original_results_unchanged':True,
            'independent_verification_approval':False,'scope':checked['result'],
            'run_report_sha256':sha(run/'run.json'),'subset_manifest_sha256':sha(subset_path),
            'source_train_is_historical_model_training_proof':False,'near_duplicates_checked':False,
            'subset_counts':manifest['subset_counts'],'conditions':conditions}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run_dir',type=Path);p.add_argument('subset_manifest',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args()
    result=recalculate(a.run_dir,a.subset_manifest,a.repo_root)
    with a.output.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
