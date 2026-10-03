"""Isolated Square Attack evaluation of manifest-verified ship images."""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import numpy as np
from adversarial_ai.attacks.square import square_linf
from adversarial_ai.evaluation.integrity import sha256_file, _resolve_dataset_file

ROOT = Path(__file__).resolve().parents[3]


def summarize(rows, budget):
    correct = [r for r in rows if r['clean_pred'] == r['true_index']]
    successes = [r for r in correct if r['attacked_pred'] != r['true_index']]
    return dict(samples=len(rows), clean_correct=len(correct),
                attacked_correct=sum(r['attacked_pred']==r['true_index'] for r in rows),
                clean_accuracy=len(correct)/len(rows),
                attacked_accuracy=sum(r['attacked_pred']==r['true_index'] for r in rows)/len(rows),
                asr_successes=len(successes), asr_denominator=len(correct),
                asr=len(successes)/len(correct) if correct else None,
                mean_total_queries=float(np.mean([r['queries'] for r in rows])),
                mean_success_queries=float(np.mean([r['queries'] for r in successes])) if successes else None,
                success_by_total_queries={str(q):sum(r['queries']<=q for r in successes)
                    for q in sorted({1, min(10,budget), min(50,budget), budget})})


def run(args):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',args.run_id):
        raise ValueError('invalid run id')
    if args.per_class < 0 or args.batch_size < 1:
        raise ValueError('invalid sample or batch count')
    classes = json.loads((ROOT/'configs/classes.json').read_text())
    names = [classes[str(i)] for i in range(10)]
    manifest_path = ROOT/'configs/test_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    model_path = ROOT/'models'/('cnn_baseline.h5' if args.model=='cnn' else 'mobilenet_finetuned.h5')
    model_hash = sha256_file(model_path)
    expected = next(m['sha256'] for m in manifest['models'] if m['path']==str(model_path.relative_to(ROOT)))
    if model_hash != expected:
        raise ValueError('model hash mismatch')
    records = []
    for name in names:
        group = [r for r in manifest['test_files'] if r['label']==name]
        records.extend(group[:args.per_class] if args.per_class else group)
    for record in records:
        path = _resolve_dataset_file(args.data_dir,record['relative_path'])
        if sha256_file(path)!=record['sha256']:
            raise ValueError('image hash mismatch: '+record['relative_path'])
    if subprocess.check_output(['git','status','--porcelain','--','src','configs'],cwd=ROOT,text=True).strip():
        raise ValueError('commit source/config changes before evaluation')
    import tensorflow as tf
    model = tf.keras.models.load_model(model_path,compile=False)
    weights = [v.numpy().copy() for v in model.weights]
    size = 128 if args.model=='cnn' else 224
    if args.defense=='mean':
        from adversarial_ai.defenses.mean import MeanDefendedModel
        inference = MeanDefendedModel(model)
    elif args.defense=='gaussian':
        from adversarial_ai.defenses.gaussian import GaussianDefendedModel
        inference = GaussianDefendedModel(model)
    else:
        inference = model

    @tf.function(input_signature=[tf.TensorSpec([None,size,size,3],tf.float32)])
    def predict(x):
        return inference(x,training=False)

    base = ROOT/'results/extensions/square'
    for path in (ROOT/'results',ROOT/'results/extensions',base):
        if path.is_symlink():
            raise ValueError('output symlink not allowed')
    out = base/args.run_id
    out.mkdir(parents=True,exist_ok=False)
    report = dict(status='RUNNING',kind='square_linf_extension',
        started_at=datetime.now(timezone.utc).isoformat(),
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        settings={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
        model_sha256=model_hash,manifest_sha256=sha256_file(manifest_path),
        classes_sha256=sha256_file(ROOT/'configs/classes.json'),
        scope='full_781' if not args.per_class else 'fixed_manifest_prefix_per_class_pilot',
        tensorflow=tf.__version__,keras=tf.keras.__version__,numpy=np.__version__,
        python=platform.python_version(),platform=platform.platform(),
        devices=[d.device_type for d in tf.config.list_physical_devices()],
        environment={k:os.environ.get(k) for k in ('TF_ENABLE_ONEDNN_OPTS','TF_DETERMINISTIC_OPS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS')},
        score_space='model_native_output',query_accounting='includes clean query; excludes no extra verification queries',
        pipeline='direct_attack_on_filter_then_model' if args.defense!='none' else 'direct_attack_on_model',
        independent_verification_approval=False,conditions=[])
    def save():
        temp=out/'run.json.tmp'
        temp.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
        temp.replace(out/'run.json')
    save()
    try:
        for eps in args.epsilons:
            rows=[]
            for start in range(0,len(records),args.batch_size):
                batch=records[start:start+args.batch_size]
                x=np.stack([tf.keras.utils.img_to_array(tf.keras.utils.load_img(
                    args.data_dir/r['relative_path'],target_size=(size,size),interpolation='nearest'))/255. for r in batch]).astype(np.float32)
                y=np.array([names.index(r['label']) for r in batch])
                result=square_linf(predict,x,y,epsilon=eps,max_queries=args.max_queries,
                                   p_init=args.p_init,seed=args.seed+start)
                norms=np.max(np.abs(result.adversarial-x),axis=(1,2,3))
                if np.max(norms)>eps+1e-6:
                    raise ValueError('perturbation budget exceeded')
                for i,record in enumerate(batch):
                    rows.append(dict(relative_path=record['relative_path'],image_sha256=record['sha256'],
                        true_index=int(y[i]),clean_pred=int(result.clean_predictions[i]),
                        attacked_pred=int(result.predictions[i]),queries=int(result.queries[i]),
                        linf=float(norms[i]),final_margin=float(result.margins[i])))
                print(f'epsilon={eps:g} {len(rows)}/{len(records)}',flush=True)
            file=out/f'eps_{eps:g}.csv'
            with file.open('x',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            report['conditions'].append(dict(epsilon=eps,csv=file.name,sha256=sha256_file(file),metrics=summarize(rows,args.max_queries)))
            save()
        if any(not np.array_equal(a,b.numpy()) for a,b in zip(weights,model.weights)):
            raise ValueError('model weights changed')
        report['status']='COMPLETED_PILOT' if args.per_class else 'COMPLETED_NOT_INDEPENDENT_APPROVAL'
    except BaseException as exc:
        report['status']='ERROR';report['error']=f'{type(exc).__name__}: {exc}'
        raise
    finally:
        report['finished_at']=datetime.now(timezone.utc).isoformat();save()
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',choices=['cnn','mobilenet'],default='cnn')
    p.add_argument('--defense',choices=['none','mean','gaussian'],default='none')
    p.add_argument('--data-dir',type=Path,default=ROOT/'data/test')
    p.add_argument('--per-class',type=int,default=2,help='manifest prefix per class; 0 = all 781')
    p.add_argument('--epsilons',type=float,nargs='+',default=[0,.01,.03,.05])
    p.add_argument('--max-queries',type=int,default=1000)
    p.add_argument('--p-init',type=float,default=.05)
    p.add_argument('--seed',type=int,default=2026)
    p.add_argument('--batch-size',type=int,default=20)
    p.add_argument('--run-id',required=True)
    print(run(p.parse_args()))


if __name__=='__main__':
    main()
