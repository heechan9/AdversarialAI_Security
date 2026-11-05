"""Evaluate one audited CNN pair on the canonical test split; no training."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--backup', type=Path, required=True)
    p.add_argument('--test-dir', type=Path, required=True)
    p.add_argument('--batch-id', required=True)
    p.add_argument('--seed', type=int, default=2026)
    args = p.parse_args()
    root = args.repo.resolve()
    os.chdir(root)
    sys.path[:0] = [str(root / 'src'), str(root)]
    import numpy as np
    import tensorflow as tf
    from adversarial_ai.attacks.iterative import generate_iterative
    from adversarial_ai.attacks.fgsm import infer_from_logits
    from adversarial_ai.evaluation.integrity import validate_reproducibility_manifest
    from verification.training_control_audit import audit
    if not tf.config.list_physical_devices('GPU'):
        raise RuntimeError('GPU unavailable; refusing CPU evaluation')
    pin = 'db3bfe6b79d3cecb2ef57aeaaf29ab9d89b5d9bf'
    if subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip() != pin:
        raise RuntimeError('Source revision mismatch')
    if subprocess.check_output(['git','status','--porcelain','--','src','configs','verification'], text=True).strip():
        raise RuntimeError('Source/config changed')
    runs = {mode:root/'results/extensions/adversarial_training'/f'{args.batch_id}_{mode}_s{args.seed}'
            for mode in ('clean_only','pgd_mixed')}
    paired = audit(runs['clean_only'], runs['pgd_mixed'])
    output = args.backup/f'test_pgd7_pgd50_r5_s{args.seed}_v2'
    output.mkdir(exist_ok=False)
    def write(name, data):
        temporary = output/(name+'.tmp')
        temporary.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')
        temporary.replace(output/name)
    write('paired-audit.json', paired)
    names = [json.loads((root/'configs/classes.json').read_text())[str(i)] for i in range(10)]
    gen = tf.keras.preprocessing.image.ImageDataGenerator(rescale=1./255).flow_from_directory(
        str(args.test_dir), target_size=(128,128), batch_size=8, class_mode='categorical', shuffle=False)
    if gen.n != 781 or gen.class_indices != {n:i for i,n in enumerate(names)}:
        raise RuntimeError('Unexpected test split or class order')
    original = root/'models/cnn_baseline.h5'
    baseline_hash = validate_reproducibility_manifest(manifest_path=root/'configs/test_manifest.json',
        model_path=Path('models/cnn_baseline.h5'),dataset_filenames=gen.filenames,data_dir=args.test_dir)
    model_paths = {'baseline':original, **{k:v/'best.keras' for k,v in runs.items()}}
    report = dict(status='RUNNING',scope='CNN unfiltered canonical test split, one matched seed',
        started_at=datetime.now(timezone.utc).isoformat(),source_commit=pin,
        evaluator_sha256=sha(__file__),paired_audit=paired,
        test_manifest_sha256=sha(root/'configs/test_manifest.json'),baseline_sha256=baseline_hash,
        settings=dict(seed=args.seed,batch_size=8,epsilon=.03,step_size=.005,
                      pgd7=dict(steps=7,restarts=1),pgd50=dict(steps=50,restarts=5)),
        models={},independent_verification_approval=False,
        limitations=['One seed only; no independent reproduction or external data.',
                     'Exact split overlap checks do not establish vessel/scene independence.',
                     'Historical baseline training exposure is unresolved.',
                     'No preprocessing defenses, AutoAttack, or certified robustness evaluation.'])
    write('evaluation.json',report)
    try:
        for name,path in model_paths.items():
            expected = baseline_hash if name=='baseline' else paired['model_sha256'][name]
            if sha(path)!=expected: raise RuntimeError('Model hash mismatch: '+name)
            model=tf.keras.models.load_model(path,compile=False)
            before=[v.numpy().copy() for v in model.weights]
            logits=infer_from_logits(model)
            rows=[]
            csv_path=output/(name+'.csv')
            fields=['relative_path','true_index','clean_pred','pgd7_pred','pgd50_pred','pgd7_linf','pgd50_linf']
            with csv_path.open('x',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
                for batch in range(len(gen)):
                    x,y=gen[batch]
                    def predict(z):
                        values=np.asarray(model(z,training=False))
                        if values.shape!=(len(x),10) or not np.isfinite(values).all():
                            raise RuntimeError('Invalid model output')
                        return values.argmax(axis=1)
                    clean=predict(x)
                    common=dict(epsilon=.03,step_size=.005,attack='pgd',seed=(args.seed+batch)%(2**31),from_logits=logits)
                    a7=np.asarray(generate_iterative(model,x,y,steps=7,restarts=1,**common))
                    a50=np.asarray(generate_iterative(model,x,y,steps=50,restarts=5,**common))
                    d7=np.max(np.abs(a7-x),axis=(1,2,3));d50=np.max(np.abs(a50-x),axis=(1,2,3))
                    for value,delta in ((a7,d7),(a50,d50)):
                        if not np.isfinite(value).all() or value.min() < 0 or value.max() > 1 or delta.max() > .030001:
                            raise RuntimeError('Attack constraint violated')
                    pred7=predict(a7);pred50=predict(a50)
                    for j in range(len(x)):
                        row=dict(relative_path=gen.filenames[batch*8+j].replace('\\','/'),true_index=int(y[j].argmax()),
                            clean_pred=int(clean[j]),pgd7_pred=int(pred7[j]),pgd50_pred=int(pred50[j]),
                            pgd7_linf=float(d7[j]),pgd50_linf=float(d50[j]))
                        rows.append(row);writer.writerow(row)
                    stream.flush()
                    print(f'TEST {name} batch {batch+1}/{len(gen)} PGD7 + PGD50/5 restarts',flush=True)
            if len(rows)!=781 or any(not np.array_equal(a,b.numpy()) for a,b in zip(before,model.weights)):
                raise RuntimeError('Incomplete evaluation or model mutation')
            clean_n=sum(r['clean_pred']==r['true_index'] for r in rows)
            metrics={}
            for attack in ('pgd7','pgd50'):
                successes=sum(r['clean_pred']==r['true_index'] and r[attack+'_pred']!=r['true_index'] for r in rows)
                metrics[attack]=dict(accuracy=sum(r[attack+'_pred']==r['true_index'] for r in rows)/781,
                    asr=successes/clean_n if clean_n else None,asr_successes=successes,asr_denominator=clean_n)
            report['models'][name]=dict(model_sha256=expected,samples=781,clean_accuracy=clean_n/781,
                attacks=metrics,csv=csv_path.name,csv_sha256=sha(csv_path))
            write('evaluation.json',report)
            del model
            tf.keras.backend.clear_session()
        report['status']='COMPLETED_NOT_INDEPENDENT_APPROVAL'
    except BaseException as exc:
        report['status']='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'ERROR'
        report['error']=type(exc).__name__+': '+str(exc)
        raise
    finally:
        report['updated_at']=datetime.now(timezone.utc).isoformat()
        write('evaluation.json',report)
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
