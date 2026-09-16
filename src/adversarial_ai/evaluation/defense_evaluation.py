"""Experimental, full-manifest Gaussian defense evaluation (never promotion)."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from adversarial_ai.attacks.fgsm import generate_fgsm, infer_from_logits
from adversarial_ai.defenses.gaussian import GaussianDefendedModel, generate_adaptive_fgsm
from adversarial_ai.evaluation.clean_baseline import load_expected_classes, validate_class_mapping
from adversarial_ai.evaluation.integrity import validate_reproducibility_manifest, sha256_file

EPSILONS = (0., .01, .03, .05)
MODELS = (("cnn", "models/cnn_baseline.h5", 128, "cnn_baseline_eval.csv"),
          ("mobilenet", "models/mobilenet_finetuned.h5", 224, "mobilenet_eval.csv"))
PREDICTIONS = ("clean", "defended_clean", "attacked", "transfer_defended", "adaptive_defended")


def _write_json(path, value):
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)


def prepare_output(path, repo):
    """Require a new directory outside the research checkout; no overwrite."""
    path, repo = Path(path).resolve(), Path(repo).resolve()
    if path == repo or repo in path.parents or path in repo.parents:
        raise ValueError('output must be a new directory outside the repository')
    path.mkdir(parents=True, exist_ok=False)
    return path


def summarize(frame):
    """Recalculate all metrics from sample rows. Empty denominators are null."""
    true = frame.true_index.to_numpy()
    predictions = {key: frame[key + '_pred'].to_numpy() for key in PREDICTIONS}
    base = predictions['clean'] == true
    defended = predictions['defended_clean'] == true
    common = base & defended
    def rate(mask, pred):
        den = int(mask.sum())
        num = int((mask & (pred != true)).sum())
        return dict(successes=num, denominator=den, asr=num/den if den else None)
    return {
        'samples': len(frame),
        'accuracy': {key: float(np.mean(p == true)) if len(frame) else None for key,p in predictions.items()},
        'clean_harmed': int((base & ~defended).sum()),
        'clean_recovered': int((~base & defended).sum()),
        'asr_original': rate(base, predictions['attacked']),
        'asr_transfer_defended': rate(defended, predictions['transfer_defended']),
        'asr_adaptive_defended': rate(defended, predictions['adaptive_defended']),
        'common_clean_correct': {key: rate(common, predictions[key])
            for key in ('attacked','transfer_defended','adaptive_defended')},
    }


def validate_rows(frame, canonical, filenames, epsilon, nclasses):
    expected = ['relative_path','epsilon','true_index'] + [k+'_pred' for k in PREDICTIONS] + ['original_linf','adaptive_linf']
    if list(frame.columns) != expected or len(frame) != len(filenames):
        raise ValueError('sample schema/count mismatch')
    normalize = lambda values: [str(p).replace('\\','/') for p in values]
    if normalize(frame.relative_path) != normalize(filenames) or normalize(canonical.relative_path) != normalize(filenames):
        raise ValueError('canonical path/order mismatch')
    if len(set(normalize(filenames))) != len(filenames):
        raise ValueError('duplicate paths')
    for col in ['true_index'] + [k+'_pred' for k in PREDICTIONS]:
        a = pd.to_numeric(frame[col], errors='raise').to_numpy()
        if not np.isfinite(a).all() or np.any(a != np.floor(a)) or np.any(a < 0) or np.any(a >= nclasses):
            raise ValueError('invalid class index')
    if not np.array_equal(frame.true_index, canonical.true_index) or not np.array_equal(frame.clean_pred, canonical.predicted_index):
        raise ValueError('clean predictions/labels differ from canonical evidence; stop for review')
    if not np.all(frame.epsilon == epsilon):
        raise ValueError('epsilon mismatch')
    for col in ('original_linf','adaptive_linf'):
        a = frame[col].to_numpy()
        if not np.isfinite(a).all() or np.any(a < 0) or np.any(a > epsilon + 1e-6):
            raise ValueError('invalid perturbation bound')
    if epsilon == 0:
        if not (frame.original_linf.eq(0).all() and frame.adaptive_linf.eq(0).all()
                and frame.clean_pred.equals(frame.attacked_pred)
                and frame.defended_clean_pred.equals(frame.transfer_defended_pred)
                and frame.defended_clean_pred.equals(frame.adaptive_defended_pred)):
            raise ValueError('epsilon zero invariant failed')


def _indices(outputs, from_logits, nclasses):
    import tensorflow as tf
    a = np.asarray(tf.nn.softmax(outputs, axis=1) if from_logits else outputs)
    if a.ndim != 2 or a.shape[1] != nclasses or not np.isfinite(a).all():
        raise ValueError('invalid model output shape/finiteness')
    if np.any(a < 0) or np.any(a > 1) or not np.allclose(a.sum(axis=1),1,atol=1e-5,rtol=0):
        raise ValueError('invalid model probabilities')
    if np.any((a == a.max(axis=1,keepdims=True)).sum(axis=1) != 1):
        raise ValueError('ambiguous model argmax')
    return a.argmax(axis=1)


def evaluate_batch(model, images, labels, epsilon, from_logits, nclasses):
    defended = GaussianDefendedModel(model)
    original = np.asarray(generate_fgsm(model, images, labels, epsilon, from_logits=from_logits))
    adaptive = np.asarray(generate_adaptive_fgsm(model, images, labels, epsilon))
    for a in (original, adaptive):
        if a.shape != images.shape or not np.isfinite(a).all() or np.any(a < 0) or np.any(a > 1):
            raise ValueError('invalid adversarial array')
        if np.max(np.abs(a-images)) > epsilon + 1e-6:
            raise ValueError('attack exceeds input budget')
        if epsilon == 0 and not np.array_equal(a, images):
            raise ValueError('epsilon zero changed pixels')
    outputs = (model(images,training=False), defended(images), model(original,training=False),
               defended(original), defended(adaptive))
    data = {key+'_pred': _indices(value,from_logits,nclasses) for key,value in zip(PREDICTIONS,outputs)}
    data.update(true_index=np.argmax(labels,axis=1),
                original_linf=np.max(np.abs(original-images),axis=(1,2,3)),
                adaptive_linf=np.max(np.abs(adaptive-images),axis=(1,2,3)))
    return data


def run(output):
    import tensorflow as tf
    repo = Path.cwd().resolve()
    source_repo = Path(__file__).resolve().parents[3]
    source_sha = subprocess.run(['git','rev-parse','HEAD'],cwd=source_repo,check=True,
                                capture_output=True,text=True,timeout=10).stdout.strip()
    classes_path = Path('configs/classes.json')
    manifest_path = Path('configs/test_manifest.json')
    classes = load_expected_classes(classes_path)
    # Validate all assets before creating outputs or loading either model.
    generators = {}
    for name, modelpath, size, cleanfile in MODELS:
        gen = tf.keras.preprocessing.image.ImageDataGenerator(rescale=1./255).flow_from_directory(
            'data/test', target_size=(size,size), batch_size=32, class_mode='categorical', shuffle=False)
        validate_class_mapping(gen.class_indices, classes)
        validate_reproducibility_manifest(manifest_path=manifest_path,model_path=Path(modelpath),
                                         dataset_filenames=gen.filenames,data_dir=Path('data/test'))
        canonical = pd.read_csv(Path('results/clean') / cleanfile)
        if len(canonical) != gen.samples:
            raise ValueError('canonical sample count mismatch')
        generators[name] = (gen, canonical)
    paths = [manifest_path,classes_path] + [Path(m[1]) for m in MODELS] + [Path('results/clean')/m[3] for m in MODELS]
    inputs_before = {p.as_posix():sha256_file(p) for p in paths}
    output = prepare_output(output,repo)
    try:
        _write_json(output/'contract.json', dict(status='experimental',promoted=False,source_sha=source_sha,
            source_files={p.relative_to(source_repo).as_posix():sha256_file(p) for p in
                (Path(__file__).resolve(),source_repo/'src/adversarial_ai/defenses/gaussian.py',
                 source_repo/'src/adversarial_ai/attacks/fgsm.py')},
            python=platform.python_version(),tensorflow=tf.__version__,keras=tf.keras.__version__,
            started_utc=datetime.now(timezone.utc).isoformat(),inputs_sha256=inputs_before,
            epsilons=EPSILONS,defense='fixed 3x3 binomial /16, REFLECT, NHWC',
            evaluation='full manifest; inference executed locally; no promotion',
            asr_denominator='clean-correct for the evaluated pipeline; common subset separately',
            pixel_evidence='bounds/clipping checked in memory; raw arrays not exported'))
        summaries = []
        for name,modelpath,size,cleanfile in MODELS:
            gen,canonical = generators[name]
            model = tf.keras.models.load_model(modelpath)
            logits = infer_from_logits(model)
            before = [w.numpy().copy() for w in model.weights]
            reference = None
            for epsilon in EPSILONS:
                parts=[]
                for b in range(len(gen)):
                    x,y=gen[b]
                    part=pd.DataFrame(evaluate_batch(model,x,y,epsilon,logits,len(classes)))
                    part.insert(0,'epsilon',epsilon)
                    start=b*gen.batch_size
                    part.insert(0,'relative_path',[p.replace('\\','/') for p in gen.filenames[start:start+len(x)]])
                    part=part[['relative_path','epsilon','true_index']+[k+'_pred' for k in PREDICTIONS]+['original_linf','adaptive_linf']]
                    parts.append(part)
                    print(f'{name} epsilon={epsilon:g} batch {b+1}/{len(gen)}',flush=True)
                frame=pd.concat(parts,ignore_index=True)
                validate_rows(frame,canonical,gen.filenames,epsilon,len(classes))
                clean_pair=frame[['clean_pred','defended_clean_pred']].to_numpy()
                if reference is not None and not np.array_equal(reference,clean_pair):
                    raise ValueError('normal predictions changed between epsilon runs')
                reference=clean_pair
                dest=output/f'{name}_eps_{epsilon:g}_samples.csv'
                frame.to_csv(dest,index=False,mode='x')
                reread=pd.read_csv(dest)
                validate_rows(reread,canonical,gen.filenames,epsilon,len(classes))
                summaries.append(dict(model=name,epsilon=epsilon,overall=summarize(reread),
                    classes={label:summarize(reread[reread.true_index==idx]) for idx,label in enumerate(classes)}))
            if len(before)!=len(model.weights) or any(not np.array_equal(a,b.numpy()) for a,b in zip(before,model.weights)):
                raise ValueError('model weights changed')
            validate_reproducibility_manifest(manifest_path=manifest_path,model_path=Path(modelpath),
                dataset_filenames=gen.filenames,data_dir=Path('data/test'))
            del model
            tf.keras.backend.clear_session()
        if inputs_before != {p.as_posix():sha256_file(p) for p in paths}:
            raise ValueError('research input files changed')
        _write_json(output/'summary.json',summaries)
        _write_json(output/'SHA256.json',{p.name:sha256_file(p) for p in sorted(output.iterdir()) if p.is_file()})
        _write_json(output/'COMPLETE.json',dict(status='experimental_completed',promoted=False,
            completed_utc=datetime.now(timezone.utc).isoformat(),weights_unchanged=True,
            inputs_unchanged=True,summary_sha256=sha256_file(output/'summary.json'),
            checksums_sha256=sha256_file(output/'SHA256.json')))
    except Exception as exc:
        _write_json(output/'FAILED.json',dict(status='failed',error=str(exc),promoted=False))
        raise
    print(f'EXPERIMENT COMPLETE (not official): {output}',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True,help='New output directory outside research repository')
    args=parser.parse_args()
    run(args.output)


if __name__ == '__main__':
    main()
