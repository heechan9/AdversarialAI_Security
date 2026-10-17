"""Targeted JSMA follow-up, explicitly reporting partial/step-capped coverage."""
import argparse
import csv
from datetime import datetime,timezone
import json
from pathlib import Path
import platform
import subprocess
import os
import numpy as np
from adversarial_ai.attacks.jsma import generate_jsma
from adversarial_ai.attacks.fgsm import infer_from_logits
from adversarial_ai.evaluation.integrity import validate_reproducibility_manifest,sha256_file


def inherit_rows(parent_dir, out, report, root):
    """Freeze and audit a prefix; require identical code, inputs and runtime."""
    from verification.jsma_saved_audit import audit
    parent_dir=Path(parent_dir)
    if parent_dir.is_symlink() or (parent_dir/'run.json').is_symlink():
        raise ValueError('unsafe parent')
    raw=(parent_dir/'run.json').read_bytes();parent=json.loads(raw)
    for key in ('kind','source_commit','model_sha256','manifest_sha256','tensorflow','keras','platform','environment','python','numpy'):
        if key not in parent or parent[key]!=report[key]:raise ValueError('resume identity mismatch: '+key)
    for key in ('model','defense','theta','gamma','max_steps','limit'):
        if parent['settings'][key]!=report['settings'][key]:raise ValueError('resume setting mismatch: '+key)
    import tempfile,hashlib
    with tempfile.TemporaryDirectory(dir=out) as temporary:
        frozen=Path(temporary);(frozen/'run.json').write_bytes(raw);audit(frozen,root)
    (out/'parent-run.json').write_bytes(raw)
    report['continuation']={'parent_report_sha256':hashlib.sha256(raw).hexdigest(),'inherited_samples':len(parent['rows'])}
    report['rows']=parent['rows'];report['evaluated']=len(parent['rows'])


def main():
    import tensorflow as tf
    from adversarial_ai.defenses.gaussian import GaussianDefendedModel
    from adversarial_ai.defenses.mean import MeanDefendedModel
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',choices=['cnn','mobilenet'],required=True)
    p.add_argument('--defense',choices=['none','gaussian','mean'],default='none')
    p.add_argument('--theta',type=float,required=True);p.add_argument('--gamma',type=float,required=True)
    p.add_argument('--max-steps',type=int,required=True);p.add_argument('--limit',type=int,default=781)
    p.add_argument('--run-id',required=True);p.add_argument('--data-dir',type=Path,default=Path('data/test'))
    p.add_argument('--resume-from',type=Path)
    args=p.parse_args();root=Path(__file__).resolve().parents[3]
    if Path.cwd().resolve()!=root:raise ValueError('run from repository root')
    if not 1<=args.limit<=781:raise ValueError('limit in [1,781] required')
    import re,math
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,79}',args.run_id):raise ValueError('invalid run id')
    if not math.isfinite(args.theta) or not 0<abs(args.theta)<=1 or not math.isfinite(args.gamma) or not 0<=args.gamma<=1 or args.max_steps<1:raise ValueError('invalid JSMA settings')
    if subprocess.check_output(['git','status','--porcelain','--','src','configs'],text=True).strip():raise ValueError('commit source/config before execution')
    source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    classes=json.loads((root/'configs/classes.json').read_text());names=[classes[str(i)] for i in range(10)]
    size=128 if args.model=='cnn' else 224
    gen=tf.keras.preprocessing.image.ImageDataGenerator(rescale=1./255).flow_from_directory(str(args.data_dir),target_size=(size,size),batch_size=1,shuffle=False)
    if gen.class_indices!={n:i for i,n in enumerate(names)}:raise ValueError('class mapping differs')
    path=Path('models')/('cnn_baseline.h5' if args.model=='cnn' else 'mobilenet_finetuned.h5')
    model_hash=validate_reproducibility_manifest(manifest_path=root/'configs/test_manifest.json',model_path=path,dataset_filenames=gen.filenames,data_dir=args.data_dir)
    model=tf.keras.models.load_model(path,compile=False);logits=infer_from_logits(model)
    attacked=model if args.defense=='none' else (GaussianDefendedModel if args.defense=='gaussian' else MeanDefendedModel)(model)
    out=root/'results/extensions/jsma'/args.run_id
    if any(p.is_symlink() for p in [out,*out.parents]):raise ValueError('unsafe output')
    out.mkdir(parents=True,exist_ok=False)
    report=dict(kind='targeted_jsma_followup',status='RUNNING',source_commit=source,model_sha256=model_hash,
        manifest_sha256=sha256_file(root/'configs/test_manifest.json'),settings={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items()},
        target_policy='(true_index + 1) % 10',attack_path='undefended' if args.defense=='none' else 'defense_aware',
        l0_unit='scalar_channel_feature',test_inventory=781,evaluated=0,rows=[],
        tensorflow=tf.__version__,keras=tf.keras.__version__,platform=platform.platform(),
        python=platform.python_version(),numpy=np.__version__,
        environment={k:os.environ.get(k) for k in ('TF_ENABLE_ONEDNN_OPTS','TF_DETERMINISTIC_OPS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS')},
        started_at=datetime.now(timezone.utc).isoformat())
    def save():
        temporary=out/'run.json.tmp'
        temporary.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');temporary.replace(out/'run.json')
    save()
    try:
        if args.resume_from is not None:inherit_rows(args.resume_from,out,report,root);save()
        for i in range(report['evaluated'],args.limit):
            x,y=gen[i];truth=int(y.argmax(1)[0]);target=(truth+1)%10
            clean=int(np.asarray(attacked(x,training=False)).argmax(1)[0])
            adv,info=generate_jsma(attacked,x,target,theta=args.theta,gamma=args.gamma,max_steps=args.max_steps,from_logits=logits)
            pred=int(np.asarray(attacked(adv,training=False)).argmax(1)[0])
            report['rows'].append(dict(relative_path=gen.filenames[i].replace('\\','/'),true_index=truth,clean_pred=clean,adversarial_pred=pred,**info))
            report['evaluated']=len(report['rows']);save()
            print(f'{args.model} {args.defense} {i+1}/{args.limit}: {info["termination"]}',flush=True)
        rows=report['rows'];eligible=[r for r in rows if r['clean_pred']==r['true_index']]
        report['targeted_asr_clean_correct']=sum(r['target_success'] for r in eligible)/len(eligible) if eligible else None
        report['asr_denominator']=len(eligible)
        report['accuracy']=sum(r['adversarial_pred']==r['true_index'] for r in rows)/len(rows)
        report['step_limited_samples']=sum(r['termination']=='step_limit' for r in rows)
        report['status']='FULL_COVERAGE_NOT_ROBUSTNESS_PROOF' if len(rows)==781 else 'PARTIAL_COVERAGE_NOT_FULL_EVALUATION'
    except KeyboardInterrupt:
        report['status']='INTERRUPTED';raise
    except Exception as exc:report['status']='ERROR';report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:report['finished_at']=datetime.now(timezone.utc).isoformat();save()
    print(out)

if __name__=='__main__':main()
