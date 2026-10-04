"""Pinned official SurFree on manifest-verified CNN images, top-1 only."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import numpy as np
from adversarial_ai.attacks.surfree_adapter import load_official,attack_one,UPSTREAM_COMMIT,HASHES
from adversarial_ai.evaluation.integrity import sha256_file,_resolve_dataset_file

ROOT=Path(__file__).resolve().parents[3]


def summarize(rows):
    correct=[r for r in rows if r['clean_pred']==r['true_index']]
    success=[r for r in correct if r['successful']]
    return dict(samples=len(rows),clean_correct=len(correct),
        successful_any_distance=len(success),asr_any_distance=len(success)/len(correct) if correct else None,
        initialization_failures=sum(r['stop_reason']=='initialization_failed' for r in correct),
        mean_total_queries=float(np.mean([r['queries'] for r in rows])),
        median_success_l2=float(np.median([r['l2'] for r in success])) if success else None,
        median_success_rms=float(np.median([r['rms'] for r in success])) if success else None,
        thresholds={str(t):dict(successes=sum(r['rms']<=t for r in success),
            asr=sum(r['rms']<=t for r in success)/len(correct) if correct else None,
            accuracy=(len(correct)-sum(r['rms']<=t for r in success))/len(rows)) for t in (.01,.03,.05)})


def run(args):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',args.run_id):raise ValueError('invalid run id')
    if args.per_class<0 or args.max_queries<1 or args.seed<0:raise ValueError('invalid settings')
    official=load_official(args.upstream)
    import torch
    import tensorflow as tf
    torch.set_num_threads(1)
    classes_path=ROOT/'configs/classes.json';manifest_path=ROOT/'configs/test_manifest.json'
    names=list(json.loads(classes_path.read_text()).values())
    manifest=json.loads(manifest_path.read_text())
    training_path=ROOT/'results/extensions/cnn_adversarial_20261002/training.json'
    model_path=ROOT/'models'/('cnn_baseline.h5' if args.model_role=='original' else 'cnn_adversarial.keras')
    expected=manifest['models'][0]['sha256'] if args.model_role=='original' else json.loads(training_path.read_text())['trained_model_sha256']
    if sha256_file(model_path)!=expected:raise ValueError('model hash mismatch')
    records=[]
    for name in names:
        group=[r for r in manifest['test_files'] if r['label']==name]
        records.extend(group[:args.per_class] if args.per_class else group)
    for record in records:
        if sha256_file(_resolve_dataset_file(args.data_dir,record['relative_path']))!=record['sha256']:
            raise ValueError('image hash mismatch')
    if subprocess.check_output(['git','status','--porcelain','--','src','configs'],cwd=ROOT,text=True).strip():
        raise ValueError('commit source before running')
    model=tf.keras.models.load_model(model_path,compile=False)
    weights=[v.numpy().copy() for v in model.weights]
    @tf.function(input_signature=[tf.TensorSpec([1,128,128,3],tf.float32)])
    def labels(x):
        return tf.argmax(model(x,training=False),axis=1)
    base=ROOT/'results/extensions/surfree'
    for path in (ROOT/'results',ROOT/'results/extensions',base):
        if path.is_symlink():raise ValueError('output symlink not allowed')
    out=base/args.run_id;out.mkdir(parents=True,exist_ok=False)
    report=dict(status='RUNNING',kind='official_surfree_l2_top1_extension',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),
        upstream_commit=UPSTREAM_COMMIT,upstream_file_sha256=HASHES,
        settings={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
        model_sha256=expected,manifest_sha256=sha256_file(manifest_path),classes_sha256=sha256_file(classes_path),
        training_record_sha256=sha256_file(training_path) if args.model_role=='trained' else None,
        tensorflow=tf.__version__,keras=tf.keras.__version__,torch=torch.__version__,numpy=np.__version__,
        python=platform.python_version(),platform=platform.platform(),
        environment={k:os.environ.get(k) for k in ('TF_ENABLE_ONEDNN_OPTS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS')},
        query_accounting='all actual top1 queries including clean, initialization, duplicate and placeholder queries',
        norm='L2; RMS thresholds are L2/sqrt(128*128*3), not Linf epsilon',
        initialization='clipped x + 0.5 Gaussian noise; at most min(200,budget-1) attempts',
        upstream_parameters=dict(steps=args.max_queries,BS_gamma=.01,BS_max_iteration=10,rho=.98,T=1,theta_max=30,n_ortho=10,
            with_distance_line_search=False,with_interpolation=False,with_alpha_line_search=True,quantification=False,
            final_line_search=True,basis_type='dct',dct_type='full',function='constant',frequence_range=[0,.5]),
        independent_verification_approval=False,started_at=datetime.now(timezone.utc).isoformat(),completed_samples=0)
    def save():
        temp=out/'run.json.tmp';temp.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');temp.replace(out/'run.json')
    save();rows=[]
    try:
        with (out/'samples.jsonl').open('x') as f:
            for idx,record in enumerate(records):
                x=tf.keras.utils.img_to_array(tf.keras.utils.load_img(args.data_dir/record['relative_path'],
                    target_size=(128,128),interpolation='nearest')).astype(np.float32)/255.
                row=attack_one(labels,x,names.index(record['label']),official,max_queries=args.max_queries,seed=args.seed+idx)
                row.update(relative_path=record['relative_path'],image_sha256=record['sha256'],true_index=names.index(record['label']))
                f.write(json.dumps(row,allow_nan=False)+'\n');f.flush();rows.append(row)
                report['completed_samples']=len(rows)
                if len(rows)%10==0:save();print(f'{args.model_role}: {len(rows)}/{len(records)}',flush=True)
        if any(not np.array_equal(a,b.numpy()) for a,b in zip(weights,model.weights)):raise ValueError('model changed')
        report['metrics']=summarize(rows);report['samples_sha256']=sha256_file(out/'samples.jsonl')
        report['status']='COMPLETED_PILOT' if args.per_class else 'COMPLETED_NOT_INDEPENDENT_APPROVAL'
    except BaseException as exc:
        report['status']='ERROR';report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:
        report['finished_at']=datetime.now(timezone.utc).isoformat();save()
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upstream',type=Path,required=True)
    p.add_argument('--model-role',choices=['original','trained'],required=True)
    p.add_argument('--data-dir',type=Path,default=ROOT/'data/test')
    p.add_argument('--max-queries',type=int,default=1000)
    p.add_argument('--seed',type=int,default=2026)
    p.add_argument('--per-class',type=int,default=0)
    p.add_argument('--run-id',required=True)
    print(run(p.parse_args()))


if __name__=='__main__':main()
