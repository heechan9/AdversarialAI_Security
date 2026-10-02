"""PGD adversarial fine-tuning with immutable source model and split audit."""
import argparse
import hashlib
import json
from pathlib import Path
import math
import shutil
from adversarial_ai.training.checkpoints import save_snapshot, latest_snapshot
import numpy as np
from PIL import Image
from adversarial_ai.attacks.iterative import generate_iterative, validate_settings
from adversarial_ai.attacks.fgsm import infer_from_logits
from adversarial_ai.evaluation.integrity import sha256_file

EXTENSIONS={'.jpg','.jpeg','.png','.bmp','.tif','.tiff'}


def image_record(path,root):
    with Image.open(path) as im:
        rgb=im.convert('RGB');pixel=hashlib.sha256(str(rgb.size).encode()+rgb.tobytes()).hexdigest()
    return dict(path=path.relative_to(root).as_posix(),sha256=sha256_file(path),pixel_sha256=pixel)


def audit_splits(train_dir,val_dir,test_dir,manifest_path,classes):
    """Reject raw or decoded RGB exact overlap; not a near-duplicate detector."""
    manifest=json.loads(Path(manifest_path).read_text())
    if manifest['test_samples']!=781 or len(manifest['test_files'])!=781:raise ValueError('locked test manifest required')
    test_root=Path(test_dir).resolve();test_rows=[]
    expected={r['relative_path'] for r in manifest['test_files']}
    actual={p.relative_to(test_root).as_posix() for p in test_root.rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('test inventory mismatch')
    for r in manifest['test_files']:
        p=test_root/r['relative_path']
        if p.is_symlink() or not p.resolve().is_relative_to(test_root):raise ValueError('unsafe test path')
        row=image_record(p,test_root)
        if row['sha256']!=r['sha256']:raise ValueError('test hash mismatch')
        test_rows.append(row)
    splits={'test':test_rows}
    for name,root in [('train',Path(train_dir)),('validation',Path(val_dir))]:
        if root.is_symlink() or not root.is_dir():raise ValueError(f'{name} directory missing/unsafe')
        rows=[]
        for label in classes:
            folder=root/label
            if not folder.is_dir() or folder.is_symlink():raise ValueError(f'missing class {label}')
            files=sorted(folder.rglob('*'))
            selected=[]
            for p in files:
                if p.is_symlink():raise ValueError('symlinks not allowed')
                if p.is_file():
                    if p.suffix.lower() not in EXTENSIONS:raise ValueError('unsupported training file')
                    selected.append(p)
            if not selected:raise ValueError(f'empty class {label}')
            for p in selected:
                row=image_record(p,root);row['label']=label;rows.append(row)
        if {p.name for p in root.iterdir()}!=set(classes):raise ValueError('unexpected class or file')
        splits[name]=rows
    for name in ('train','validation'):
        for key in ('sha256','pixel_sha256'):
            values=[r[key] for r in splits[name]]
            if len(values)!=len(set(values)):raise ValueError(f'duplicate within {name}')
    for a,b in [('train','test'),('validation','test'),('train','validation')]:
        for key in ('sha256','pixel_sha256'):
            if {r[key] for r in splits[a]} & {r[key] for r in splits[b]}:raise ValueError(f'{a}/{b} overlap ({key})')
    return dict(kind='split_integrity_audit',manifest_sha256=sha256_file(Path(manifest_path)),splits=splits,
                near_duplicate_checked=False,note='Test data is read for overlap audit only, never training or model selection.')


def train_batch(model,optimizer,images,labels,*,epsilon,step_size,steps,seed,clean_weight=.5):
    import tensorflow as tf
    if not math.isfinite(clean_weight) or not 0<=clean_weight<=1:raise ValueError('clean_weight in [0,1] required')
    logits=infer_from_logits(model)
    adversarial=generate_iterative(model,images,labels,epsilon,step_size=step_size,steps=steps,attack='pgd',restarts=1,seed=seed,from_logits=logits)
    criterion=tf.keras.losses.CategoricalCrossentropy(from_logits=logits)
    with tf.GradientTape() as tape:
        clean_loss=criterion(labels,model(images,training=True))
        adv_loss=criterion(labels,model(tf.stop_gradient(adversarial),training=True))
        loss=clean_weight*clean_loss+(1-clean_weight)*adv_loss
        if model.losses:loss+=tf.add_n(model.losses)
    gradients=tape.gradient(loss,model.trainable_variables)
    tf.debugging.assert_all_finite(loss,'nonfinite train loss')
    if not gradients or any(g is None for g in gradients):raise RuntimeError('missing train gradients')
    for g in gradients:tf.debugging.assert_all_finite(g,'nonfinite train gradient')
    optimizer.apply_gradients(zip(gradients,model.trainable_variables))
    return float(loss)


def main():
    import tensorflow as tf
    from datetime import datetime,timezone
    import subprocess,platform
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',choices=['cnn','mobilenet'],required=True)
    for name in ('train-dir','validation-dir','test-dir'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--run-id',required=True);p.add_argument('--epochs',type=int,required=True)
    p.add_argument('--epsilon',type=float,required=True);p.add_argument('--step-size',type=float,required=True)
    p.add_argument('--steps',type=int,required=True);p.add_argument('--seed',type=int,default=2026)
    p.add_argument('--batch-size',type=int,default=32);p.add_argument('--learning-rate',type=float,default=1e-5)
    p.add_argument('--resume',action='store_true',help='Resume the latest complete epoch; unfinished epoch repeats.')
    args=p.parse_args();root=Path(__file__).resolve().parents[3]
    if Path.cwd().resolve()!=root:raise ValueError('run from repository root')
    validate_settings(args.epsilon,args.step_size,args.steps,1,args.seed,'pgd')
    if args.epochs<1 or args.batch_size<1 or not math.isfinite(args.learning_rate) or args.learning_rate<=0:raise ValueError('invalid training configuration')
    import re
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,79}',args.run_id):raise ValueError('invalid run id')
    source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if subprocess.check_output(['git','status','--porcelain','--','src','configs'],text=True).strip():raise ValueError('commit source/config first')
    classes=json.loads((root/'configs/classes.json').read_text());names=[classes[str(i)] for i in range(10)]
    audit=audit_splits(args.train_dir,args.validation_dir,args.test_dir,root/'configs/test_manifest.json',names)
    filename='cnn_baseline.h5' if args.model=='cnn' else 'mobilenet_finetuned.h5'
    path=root/'models'/filename;original_hash=sha256_file(path)
    manifest=json.loads((root/'configs/test_manifest.json').read_text())
    expected={r['path']:r['sha256'] for r in manifest['models']}
    if expected['models/'+filename]!=original_hash:raise ValueError('initial model hash mismatch')
    out=root/'results/extensions/adversarial_training'/args.run_id
    if any(p.is_symlink() for p in [out,*out.parents]):raise ValueError('unsafe output path')
    if args.resume:
        if not out.is_dir():raise ValueError('resume output missing')
    else:out.mkdir(parents=True,exist_ok=False)
    audit_text=json.dumps(audit,indent=2)+'\n'
    audit_hash=hashlib.sha256(audit_text.encode()).hexdigest()
    settings={k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items() if k!='resume'}
    identity=dict(source_commit=source,source_model_sha256=original_hash,split_audit_sha256=audit_hash,settings=settings,tensorflow=tf.__version__,keras=tf.keras.__version__)
    restored=latest_snapshot(out/'checkpoints',identity) if args.resume else None
    (out/'split-audit.json').write_text(audit_text)
    report=dict(kind='adversarial_training_followup',status='RUNNING',source_commit=source,source_model_sha256=original_hash,
        split_audit_sha256=sha256_file(out/'split-audit.json'),settings=settings,
        tensorflow=tf.__version__,keras=tf.keras.__version__,platform=platform.platform(),epochs=[],started_at=datetime.now(timezone.utc).isoformat())
    def save():
        temp=out/'training.json.tmp'
        temp.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');temp.replace(out/'training.json')
    if restored:
        report=restored[1]['report']
        report['status']='RUNNING';report.pop('finished_at',None);report.pop('error',None)
        report.setdefault('resumptions',[]).append(datetime.now(timezone.utc).isoformat())
    report['resume_policy']='completed_epoch_with_optimizer; unfinished epoch repeats; not bitwise equivalence'
    save()
    try:
        tf.keras.utils.set_random_seed(args.seed)
        original=tf.keras.models.load_model(path,compile=False)
        model=tf.keras.models.clone_model(original);model.set_weights(original.get_weights());del original
        size=128 if args.model=='cnn' else 224
        def generator(directory,shuffle):
            return tf.keras.preprocessing.image.ImageDataGenerator(rescale=1./255).flow_from_directory(str(directory),classes=names,target_size=(size,size),batch_size=args.batch_size,shuffle=shuffle,seed=args.seed)
        train=generator(args.train_dir,True);val=generator(args.validation_dir,False)
        optimizer=tf.keras.optimizers.Adam(args.learning_rate);best=-1.;start_epoch=0
        model.compile(optimizer=optimizer,loss=tf.keras.losses.CategoricalCrossentropy(from_logits=infer_from_logits(model)))
        if restored:
            snapshot,state=restored
            model=tf.keras.models.load_model(snapshot/'last.keras')
            optimizer=model.optimizer;best=state['best_score'];start_epoch=state['next_epoch']
            shutil.copy2(snapshot/'best.keras',out/'best.keras')
        for epoch in range(start_epoch,args.epochs):
            # Epoch-addressable ordering avoids generator state depending on prior batches.
            train.index_array=np.random.default_rng(args.seed+epoch).permutation(train.n)
            train.total_batches_seen=epoch*len(train)
            losses=[]
            for batch in range(len(train)):
                x,y=train[batch];losses.append(train_batch(model,optimizer,x,y,epsilon=args.epsilon,step_size=args.step_size,steps=args.steps,seed=(args.seed+epoch*len(train)+batch)%(2**31)))
                print(f'epoch {epoch+1}/{args.epochs} batch {batch+1}/{len(train)} loss {losses[-1]:.6f}',flush=True)
            clean_correct=adv_correct=total=0
            for batch in range(len(val)):
                x,y=val[batch];truth=y.argmax(1)
                adv=generate_iterative(model,x,y,args.epsilon,step_size=args.step_size,steps=args.steps,attack='pgd',restarts=1,seed=(args.seed+batch)%(2**31))
                clean_correct+=int((np.asarray(model(x,training=False)).argmax(1)==truth).sum())
                adv_correct+=int((np.asarray(model(adv,training=False)).argmax(1)==truth).sum());total+=len(x)
            score=adv_correct/total
            report['epochs'].append(dict(epoch=epoch+1,mean_batch_loss=float(np.mean(losses)),validation_samples=total,validation_clean_accuracy=clean_correct/total,validation_pgd_accuracy=score))
            if score>best:
                best=score;model.save(out/'best.keras');report['best_epoch']=epoch+1
            save_snapshot(out/'checkpoints',model,out/'best.keras',dict(identity=identity,next_epoch=epoch+1,best_score=best,report=report))
            save();train.on_epoch_end()
        if sha256_file(path)!=original_hash:raise RuntimeError('source model file changed')
        report['trained_model_sha256']=sha256_file(out/'best.keras');report['status']='TRAINED_NOT_TEST_EVALUATED'
    except KeyboardInterrupt:
        report['status']='INTERRUPTED';raise
    except Exception as exc:report['status']='ERROR';report['error']=f'{type(exc).__name__}: {exc}';raise
    finally:report['finished_at']=datetime.now(timezone.utc).isoformat();save()
    print(out)

if __name__=='__main__':main()
