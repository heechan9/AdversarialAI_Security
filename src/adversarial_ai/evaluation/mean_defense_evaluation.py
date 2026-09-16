"""Experimental, full-manifest fixed-filter defense evaluation (never promotion)."""
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
from adversarial_ai.evaluation.clean_baseline import load_expected_classes, validate_class_mapping
from adversarial_ai.evaluation.integrity import validate_reproducibility_manifest, sha256_file

EPSILONS = (0., .01, .03, .05)
MODELS = (("cnn", "models/cnn_baseline.h5", 128, "cnn_baseline_eval.csv"),
          ("mobilenet", "models/mobilenet_finetuned.h5", 224, "mobilenet_eval.csv"))
PREDICTIONS = ("clean", "defended_clean", "attacked", "transfer_defended", "adaptive_defended")


# Reuse the audited row validation, metrics, probability checks and output safety.
from adversarial_ai.evaluation.defense_evaluation import (
    _write_json, prepare_output, summarize, validate_rows, _indices,
)


def _defense_components(defense):
    if defense == 'mean':
        from adversarial_ai.defenses.mean import MeanDefendedModel, generate_adaptive_fgsm as mean_attack
        return MeanDefendedModel, mean_attack
    raise ValueError('unknown defense')


def evaluate_batch(model, images, labels, epsilon, from_logits, nclasses, defense='mean'):
    wrapper, adaptive_attack = _defense_components(defense)
    defended = wrapper(model)
    original = np.asarray(generate_fgsm(model, images, labels, epsilon, from_logits=from_logits))
    adaptive = np.asarray(adaptive_attack(model, images, labels, epsilon))
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


def run(output, defense='mean'):
    _defense_components(defense)
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
                (Path(__file__).resolve(),source_repo/f'src/adversarial_ai/defenses/{defense}.py',
                 source_repo/'src/adversarial_ai/attacks/fgsm.py',
                 source_repo/'src/adversarial_ai/evaluation/defense_evaluation.py')},
            python=platform.python_version(),tensorflow=tf.__version__,keras=tf.keras.__version__,
            started_utc=datetime.now(timezone.utc).isoformat(),inputs_sha256=inputs_before,
            epsilons=EPSILONS,defense='fixed 3x3 arithmetic mean /9, REFLECT, NHWC',defense_id=defense,
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
                    part=pd.DataFrame(evaluate_batch(model,x,y,epsilon,logits,len(classes),defense))
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
    parser.add_argument('--defense', choices=('mean',), default='mean')
    args=parser.parse_args()
    run(args.output, args.defense)


if __name__ == '__main__':
    main()
