"""Trace selected mismatches and cross-score fixed attack tensors; no approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

BASE = '491b973cd9f4840664044a83c0d62d1ee1bb98e8'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_groups(path, control_row=None):
    rows = json.loads(path.read_text(encoding='utf-8'))['targeted_results']
    groups = {}
    for row in rows:
        if (control_row is None and row['observed_off'] == int(row['reference'])) or (control_row is not None and row['row_index'] != control_row):
            continue
        method, pipeline = row['method'], row['pipeline']
        if method not in ('gaussian', 'mean') or pipeline not in ('attacked', 'transfer_defended', 'adaptive_defended'):
            raise ValueError('Unsupported selected path')
        index = row['row_index']
        if type(index) is not int or not 0 <= index < 781:
            raise ValueError('Invalid row index')
        epsilon = float(row['file'].split('_eps_')[1].split('_samples')[0])
        if epsilon not in (.01, .03, .05):
            raise ValueError('Invalid epsilon')
        key = (method, pipeline, epsilon, index//32)
        groups.setdefault(key, []).append(row)
    if not groups:
        raise ValueError('No remaining mismatches')
    return groups


def run(args):
    repo, output = args.repo_root.resolve(), args.output.resolve()
    args.selection = args.selection.resolve()
    args.other = args.other.resolve() if args.other else None
    if output.is_relative_to(repo) or repo.is_relative_to(output):
        raise ValueError('Output must be outside source checkout')
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repo, text=True)
    if sha != BASE or dirty:
        raise ValueError('Use unchanged pinned source checkout')
    mode = os.environ.get('TF_ENABLE_ONEDNN_OPTS')
    if mode is None and args.native_settings:
        mode = 'unset/native-default'
    elif mode not in ('0', '1'):
        raise ValueError('Set TF_ENABLE_ONEDNN_OPTS explicitly before launching')
    groups = selected_groups(args.selection, args.control_row)
    output.mkdir(parents=True, exist_ok=False)
    os.chdir(repo)
    sys.path.insert(0, str(repo/'src'))
    import numpy as np
    import tensorflow as tf
    from adversarial_ai.attacks.fgsm import generate_fgsm, infer_from_logits
    from adversarial_ai.defenses.gaussian import GaussianDefendedModel
    from adversarial_ai.defenses.mean import MeanDefendedModel
    from adversarial_ai.evaluation.clean_baseline import load_expected_classes, validate_class_mapping
    from adversarial_ai.evaluation.integrity import validate_reproducibility_manifest

    data = repo/'data/test'
    model_path = repo/'models/mobilenet_finetuned.h5'
    gen = tf.keras.preprocessing.image.ImageDataGenerator(rescale=1./255).flow_from_directory(
        str(data), target_size=(224,224), batch_size=32, class_mode='categorical', shuffle=False)
    validate_class_mapping(gen.class_indices, load_expected_classes(repo/'configs/classes.json'))
    validate_reproducibility_manifest(manifest_path=repo/'configs/test_manifest.json', model_path=Path('models/mobilenet_finetuned.h5'),
                                    dataset_filenames=gen.filenames, data_dir=data)
    model = tf.keras.models.load_model(model_path)
    from_logits = infer_from_logits(model)
    weights = [w.numpy().copy() for w in model.weights]
    report = dict(kind='selected_tensor_trace_not_stage_b_approval', stage_b_approved=False,
                  source_commit=sha, script_sha256=digest(Path(__file__)), selection_sha256=digest(args.selection),
                  model_sha256=digest(model_path), manifest_sha256=digest(repo/'configs/test_manifest.json'),
                  python=platform.python_version(), tensorflow=tf.__version__, keras=tf.keras.__version__,
                  platform=platform.platform(), onednn=mode, cross_only=args.cross_only, control_row=args.control_row,
                  environment={k:os.environ.get(k) for k in ('TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS','OMP_NUM_THREADS','TF_DETERMINISTIC_OPS')},
                  results=[])
    other_report = None
    if args.other:
        other_report = json.loads((args.other/'report.json').read_text())
        for key in ('source_commit', 'selection_sha256', 'model_sha256', 'manifest_sha256'):
            if other_report[key] != report[key]:
                raise ValueError('Cross-input identity mismatch: '+key)
        if other_report['execution_status'] != 'COMPLETE':
            raise ValueError('Incomplete cross-input run')

    def probabilities(values):
        p = np.asarray(values)
        if from_logits:
            p = np.asarray(tf.nn.softmax(values,axis=1))
        assert p.shape[1] == 10 and np.isfinite(p).all()
        assert np.allclose(p.sum(axis=1),1,atol=1e-5,rtol=0)
        return p

    def describe(p):
        order = np.argsort(p)[::-1]
        return dict(prediction=int(order[0]), probabilities=p.tolist(),
                    top_two=order[:2].tolist(), margin=float(p[order[0]]-p[order[1]]))

    try:
        for (method, pipeline, epsilon, batch), items in sorted(groups.items()):
            key = f'{method}-{pipeline}-{epsilon:g}-b{batch}'
            x,y = gen[batch]
            indices = [r['row_index']%32 for r in items]
            for r in items:
                assert gen.filenames[r['row_index']].replace('\\','/') == r['relative_path']
            defended = (GaussianDefendedModel if method=='gaussian' else MeanDefendedModel)(model)
            attacker = defended if pipeline=='adaptive_defended' else model
            scorer = model if pipeline=='attacked' else defended
            row = dict(key=key, method=method, pipeline=pipeline, epsilon=epsilon, batch=batch,
                       input_sha256=hashlib.sha256(x.tobytes()).hexdigest(), selected=items)
            clean_probs = probabilities(scorer(x,training=False))
            row['clean'] = [describe(clean_probs[i]) for i in indices]
            if not args.cross_only:
                tx,ty = tf.convert_to_tensor(x,tf.float32),tf.convert_to_tensor(y,tf.float32)
                loss_fn = tf.keras.losses.CategoricalCrossentropy(from_logits=from_logits,reduction=tf.keras.losses.Reduction.NONE)
                with tf.GradientTape() as tape:
                    tape.watch(tx)
                    loss = tf.reduce_mean(loss_fn(ty,attacker(tx,training=False)))
                gradient = tape.gradient(loss,tx).numpy()
                attack = tf.clip_by_value(tx+float(epsilon)*tf.sign(gradient),0.,1.).numpy()
                canonical_attack = np.asarray(generate_fgsm(attacker,x,y,epsilon,from_logits=from_logits))
                if not np.array_equal(attack,canonical_attack):
                    raise ValueError('Instrumented attack differs from pinned generate_fgsm')
                del canonical_attack
                assert np.isfinite(gradient).all() and np.max(np.abs(attack-x)) <= epsilon+1e-6
                p = probabilities(scorer(attack,training=False))
                row['native'] = [describe(p[i]) for i in indices]
                row['instrumented_attack_exact_match'] = True
                artifact = output/(key+'.npz')
                np.savez_compressed(artifact, attack=attack, gradient=gradient[indices], image=x[indices])
                row['artifact_sha256'] = digest(artifact)
                del gradient,attack
            if args.other:
                previous = next(r for r in other_report['results'] if r['key']==key)
                if previous['input_sha256'] != row['input_sha256']:
                    raise ValueError('Cross-input preprocessing differs')
                artifact = args.other/(key+'.npz')
                if digest(artifact) != previous['artifact_sha256']:
                    raise ValueError('Cross-input artifact checksum mismatch')
                with np.load(artifact,allow_pickle=False) as saved:
                    attack = saved['attack']
                    assert attack.shape == x.shape and np.isfinite(attack).all()
                    assert np.min(attack)>=0 and np.max(attack)<=1 and np.max(np.abs(attack-x))<=epsilon+1e-6
                    p = probabilities(scorer(attack,training=False))
                row['cross'] = [describe(p[i]) for i in indices]
                row['cross_source_onednn'] = other_report['onednn']
                row['cross_artifact_sha256'] = previous['artifact_sha256']
                del attack
            report['results'].append(row)
            print(key,flush=True)
        report['weights_unchanged'] = all(np.array_equal(a,w.numpy()) for a,w in zip(weights,model.weights))
        assert report['weights_unchanged']
        report['execution_status'] = 'COMPLETE'
    except BaseException:
        report['execution_status'] = 'INCOMPLETE'
        raise
    finally:
        (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,required=True)
    p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--other',type=Path)
    p.add_argument('--cross-only',action='store_true')
    p.add_argument('--control-row',type=int,help='Trace this previously reported row instead of remaining mismatches')
    p.add_argument('--native-settings',action='store_true',help='Permit an unset oneDNN variable; preserve inherited runtime settings')
    args=p.parse_args()
    if args.cross_only and not args.other:
        p.error('--cross-only requires --other')
    run(args)
