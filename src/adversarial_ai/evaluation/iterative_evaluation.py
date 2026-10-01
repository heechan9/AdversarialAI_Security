"""Isolated follow-up BIM/PGD evaluation; never overwrites ACK/Stage B evidence."""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import numpy as np
from adversarial_ai.attacks.iterative import generate_iterative, validate_settings
from adversarial_ai.attacks.fgsm import infer_from_logits
from adversarial_ai.evaluation.integrity import validate_reproducibility_manifest, sha256_file

ROOT=Path(__file__).resolve().parents[3]
PIPELINES=('clean','defended_clean','attacked','transfer_defended','adaptive_defended')


def metrics(rows):
    out={}
    for path in PIPELINES:
        baseline='defended_clean' if path in ('transfer_defended','adaptive_defended') else 'clean'
        denominator=sum(r[baseline+'_pred']==r['true_index'] for r in rows)
        successes=sum(r[baseline+'_pred']==r['true_index'] and r[path+'_pred']!=r['true_index'] for r in rows)
        out[path]={'accuracy':sum(r[path+'_pred']==r['true_index'] for r in rows)/len(rows),
                   'asr':successes/denominator if denominator else None,
                   'asr_successes':successes,'asr_denominator':denominator}
    return out


def reserve_output(run_id):
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}',run_id):raise ValueError('invalid run id')
    base=ROOT/'results'/'extensions'/'iterative'
    for path in (ROOT/'results',ROOT/'results'/'extensions',base):
        if path.is_symlink():raise ValueError('output symlink not allowed')
    out=base/run_id
    out.mkdir(parents=True,exist_ok=False)
    return out


def run(args):
    if Path.cwd().resolve()!=ROOT.resolve():raise ValueError("run from the repository root")
    validate_settings(0.05,args.step_size,args.steps,args.restarts,args.seed,args.attack)
    if args.batch_size<1:raise ValueError('positive batch size required')
    import tensorflow as tf
    from adversarial_ai.defenses.gaussian import gaussian_tensorflow, GaussianDefendedModel
    from adversarial_ai.defenses.mean import mean_tensorflow, MeanDefendedModel
    candidate=getattr(args,'trained_model',None)
    candidate_hash=getattr(args,'trained_model_sha256',None)
    candidate_kind=getattr(args,'trained_model_kind',None)
    if any(v is not None for v in (candidate,candidate_hash,candidate_kind)):
        if not all(v is not None for v in (candidate,candidate_hash,candidate_kind)):
            raise ValueError('trained model, SHA-256 and kind must be supplied together')
        if candidate_kind not in ('cnn','mobilenet') or sha256_file(Path(candidate))!=candidate_hash:
            raise ValueError('trained model identity mismatch')
    # No legacy result directory is accepted, even as a CLI override.
    out=reserve_output(args.run_id)
    report={'kind':'followup_iterative_evaluation','status':'RUNNING','independent_verification_approval':False,
            'started_at':datetime.now(timezone.utc).isoformat(),'settings':vars(args).copy(),
            'python':platform.python_version(),'platform':platform.platform(),'tensorflow':tf.__version__,
            'keras':tf.keras.__version__,'numpy':np.__version__,
            'environment':{k:os.environ.get(k) for k in ('TF_ENABLE_ONEDNN_OPTS','TF_DETERMINISTIC_OPS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS')},
            'scope':{'samples':781,'epsilons':[0,.01,.03,.05],'pipelines':list(PIPELINES)},'conditions':[]}
    report['settings']['data_dir']=str(args.data_dir)
    if candidate is not None:
        report['settings']['trained_model']=str(candidate)
        report['kind']='followup_trained_model_iterative_evaluation'
        report['trained_model_sha256']=candidate_hash
        report['scope']['models']=[candidate_kind]
    else:report['scope']['models']=['cnn','mobilenet']
    def save():
        (out/'run.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    save()
    try:
        report['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        report['source_dirty']=bool(subprocess.check_output(['git','status','--porcelain','--untracked-files=normal','--','src','configs'],cwd=ROOT,text=True).strip())
        if report['source_dirty']:raise ValueError('commit source/config changes before full evaluation')
        manifest=ROOT/'configs/test_manifest.json';report['manifest_sha256']=sha256_file(manifest)
        classes=json.loads((ROOT/'configs/classes.json').read_text())
        names=[classes[str(i)] for i in range(10)]
        report['classes_sha256']=sha256_file(ROOT/'configs/classes.json')
        for model_name,filename,size in [('cnn','cnn_baseline.h5',128),('mobilenet','mobilenet_finetuned.h5',224)]:
            if candidate is not None and model_name!=candidate_kind:continue
            generator=tf.keras.preprocessing.image.ImageDataGenerator(rescale=1./255).flow_from_directory(
                str(args.data_dir),target_size=(size,size),batch_size=args.batch_size,class_mode='categorical',shuffle=False)
            if generator.class_indices!={n:i for i,n in enumerate(names)}:raise ValueError('class order mismatch')
            model_path=Path('models')/filename
            model_hash=validate_reproducibility_manifest(manifest_path=manifest,model_path=model_path,dataset_filenames=generator.filenames,data_dir=args.data_dir)
            if candidate is not None:
                model_path=Path(candidate)
                if sha256_file(model_path)!=candidate_hash:raise ValueError('trained model changed during validation')
                model_hash=candidate_hash
            model=tf.keras.models.load_model(model_path,compile=False);logits=infer_from_logits(model)
            weights=[v.numpy().copy() for v in model.weights]
            for method,filter_fn,wrapper in [('gaussian',gaussian_tensorflow,GaussianDefendedModel),('mean',mean_tensorflow,MeanDefendedModel)]:
                defended=wrapper(model)
                for epsilon in (0.,.01,.03,.05):
                    rows=[]
                    for batch in range(len(generator)):
                        x,y=generator[batch]
                        common=dict(step_size=args.step_size,steps=args.steps,attack=args.attack,restarts=args.restarts,seed=(args.seed+batch)%(2**31),from_logits=logits)
                        adv=generate_iterative(model,x,y,epsilon,**common)
                        adaptive=generate_iterative(defended,x,y,epsilon,**common)
                        arrays={'clean':x,'defended_clean':filter_fn(x),'attacked':adv,'transfer_defended':filter_fn(adv),'adaptive_defended':filter_fn(adaptive)}
                        predictions={}
                        for key,z in arrays.items():
                            values=np.asarray(model(z,training=False))
                            if values.shape!=(len(x),10) or not np.isfinite(values).all():raise ValueError('invalid outputs')
                            predictions[key]=values.argmax(axis=1)
                        delta=np.max(np.abs(np.asarray(adv)-x),axis=(1,2,3))
                        adelta=np.max(np.abs(np.asarray(adaptive)-x),axis=(1,2,3))
                        if max(delta.max(),adelta.max())>epsilon+1e-6:raise ValueError('budget exceeded')
                        for j in range(len(x)):
                            rows.append(dict(relative_path=generator.filenames[batch*args.batch_size+j].replace('\\','/'),true_index=int(y[j].argmax()),
                                             **{k+'_pred':int(v[j]) for k,v in predictions.items()},linf=float(delta[j]),adaptive_linf=float(adelta[j])))
                        print(f'{model_name} {method} {args.attack} eps={epsilon:g} batch {batch+1}/{len(generator)}',flush=True)
                    if len(rows)!=781:raise ValueError('incomplete condition')
                    name=f'{model_name}_{method}_eps_{epsilon:g}.csv'
                    with (out/name).open('x',newline='',encoding='utf-8') as f:
                        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
                    report['conditions'].append(dict(model=model_name,model_sha256=model_hash,method=method,epsilon=epsilon,samples=len(rows),metrics=metrics(rows),csv=name,sha256=sha256_file(out/name)))
                    save()
            if any(not np.array_equal(a,b.numpy()) for a,b in zip(weights,model.weights)):raise ValueError('model mutated')
        report['status']='COMPLETED_NOT_INDEPENDENT_APPROVAL'
    except Exception as exc:
        report['status']='ERROR';report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:
        report['finished_at']=datetime.now(timezone.utc).isoformat();save()
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--attack',choices=['bim','pgd'],required=True)
    p.add_argument('--steps',type=int,required=True);p.add_argument('--step-size',type=float,required=True)
    p.add_argument('--restarts',type=int,default=1);p.add_argument('--seed',type=int,default=0)
    p.add_argument('--trained-model',type=Path)
    p.add_argument('--trained-model-sha256')
    p.add_argument('--trained-model-kind',choices=['cnn','mobilenet'])
    p.add_argument('--batch-size',type=int,default=32);p.add_argument('--run-id',required=True)
    p.add_argument('--data-dir',type=Path,default=ROOT/'data/test')
    print(run(p.parse_args()))

if __name__=='__main__':main()
