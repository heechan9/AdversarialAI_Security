"""Fail closed on missing extension evidence; no neural inference or approval."""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from verification.iterative_result_audit import audit as iterative_audit
from verification.jsma_saved_audit import audit as jsma_audit

ROOT = Path(__file__).resolve().parents[1]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    require(not path.is_symlink(), 'symlink evidence')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def audit_mobile(training_dir, evaluation_dir, root=ROOT):
    t, e, root = Path(training_dir), Path(evaluation_dir), Path(root)
    train, report = read(t/'training.json'), read(e/'evaluation.json')
    require(train['status'] == 'TRAINED_NOT_TEST_EVALUATED', 'training incomplete')
    settings = train['settings']
    for key, value in dict(model='mobilenet', epochs=3, epsilon=.03, steps=7,
                           step_size=.005, seed=2026, batch_size=8, learning_rate=1e-5).items():
        require(settings[key] == value, 'training setting: '+key)
    epochs = train['epochs']
    require([v['epoch'] for v in epochs] == [1, 2, 3], 'three ordered epochs required')
    for v in epochs:
        require(v['validation_samples'] == 689, 'validation coverage')
        require(math.isfinite(v['mean_batch_loss']), 'nonfinite loss')
        for key in ('validation_clean_accuracy', 'validation_pgd_accuracy'):
            require(math.isfinite(v[key]) and 0 <= v[key] <= 1, 'validation metric')
    best = max(epochs, key=lambda v: v['validation_pgd_accuracy'])['epoch']
    require(train['best_epoch'] == best, 'best validation epoch mismatch')
    require(digest(t/'best.keras') == train['trained_model_sha256'], 'trained weights hash')
    require(digest(t/'split-audit.json') == train['split_audit_sha256'], 'split audit hash')
    splits = read(t/'split-audit.json')
    require(splits['manifest_sha256'] == digest(root/'configs/test_manifest.json'), 'split manifest hash')
    for name, count in [('train', 6147), ('validation', 689), ('test', 781)]:
        require(len(splits['splits'][name]) == count, 'split count: '+name)
    for key in ('sha256', 'pixel_sha256'):
        sets = []
        for name in ('train', 'validation', 'test'):
            values = [v[key] for v in splits['splits'][name]]
            require(len(values) == len(set(values)), 'duplicate split hashes')
            sets.append(set(values))
        require(not (sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]), 'split overlap')
    manifest = read(root/'configs/test_manifest.json')
    require({v['path']: v['sha256'] for v in splits['splits']['test']} ==
            {v['relative_path']: v['sha256'] for v in manifest['test_files']}, 'split test identity')
    original = next(v['sha256'] for v in manifest['models'] if v['path'] == 'models/mobilenet_finetuned.h5')
    require(train['source_model_sha256'] == original, 'original model identity')
    require(report['status'] == 'COMPLETED' and report['samples'] == 781, 'evaluation incomplete')
    require(report['independent_verification_approval'] is False, 'independent approval prohibited')
    require(report['training_report_sha256'] == digest(t/'training.json'), 'training report binding')
    require(report['test_manifest_sha256'] == digest(root/'configs/test_manifest.json'), 'test manifest binding')
    for key, value in dict(epsilon=.03, steps=7, step_size=.005, restarts=1, seed=2026, batch_size=8).items():
        require(report[key] == value, 'evaluation setting: '+key)
    require(set(report['models']) == {'original', 'trained'}, 'two models required')
    labels = {v: int(k) for k, v in read(root/'configs/classes.json').items()}
    paths = [v['relative_path'] for v in manifest['test_files']]
    for kind in ('original', 'trained'):
        summary = report['models'][kind]
        path = e/(kind+'.csv')
        require(digest(path) == summary['csv_sha256'], 'evaluation CSV hash')
        with path.open(newline='') as f:
            rows = list(csv.DictReader(f))
        require(len(rows) == summary['samples'] == 781, 'evaluation row count')
        require([v['relative_path'] for v in rows] == paths, 'test order/coverage')
        for row in rows:
            for key in ('true_index', 'clean_pred', 'pgd_pred'):
                require(row[key] in [str(i) for i in range(10)], 'class index')
            require(int(row['true_index']) == labels[row['relative_path'].split('/')[0]], 'true label')
            delta = float(row['linf'])
            require(math.isfinite(delta) and 0 <= delta <= .030001, 'PGD bound')
        clean = sum(v['true_index'] == v['clean_pred'] for v in rows)
        pgd = sum(v['true_index'] == v['pgd_pred'] for v in rows)
        success = sum(v['true_index'] == v['clean_pred'] and v['true_index'] != v['pgd_pred'] for v in rows)
        require((clean, pgd) == (summary['clean_correct'], summary['pgd_correct']), 'correct counts')
        for key, value in [('clean_accuracy', clean/781), ('pgd_accuracy', pgd/781),
                           ('attack_success_rate', success/clean if clean else None)]:
            observed = summary[key]
            require(observed is None if value is None else isinstance(observed, (int, float)) and math.isfinite(observed) and abs(observed-value) <= 1e-12, 'metric: '+key)
        require(summary['sha256'] == (original if kind == 'original' else train['trained_model_sha256']), 'evaluation model binding')
    return {'result': 'SAVED_MOBILENET_EVIDENCE_CONSISTENT', 'epochs': 3, 'samples_per_model': 781,
            'independent_verification_approval': False, 'private_weights_hash_checked': True}


def audit_recovery_sources(pgd, jsma, training, evaluation):
    reports = [(pgd, 'run.json'), (jsma, 'run.json'),
               (training, 'training.json'), (evaluation, 'evaluation.json')]
    sources = [read(Path(folder)/name).get('source_commit') for folder, name in reports]
    require(all(isinstance(v, str) and re.fullmatch(r'[0-9a-f]{40}', v) for v in sources),
            'missing or invalid recovery source SHA')
    require(len(set(sources)) == 1, 'recovery stage source mismatch')
    # BIM is an immutable parent run; its different source is checked separately.
    return sources[0]


def audit_all(bim, pgd, jsma, training, evaluation, root=ROOT):
    source = audit_recovery_sources(pgd, jsma, training, evaluation)
    results = {}
    for name, folder, steps, restarts, seed, batch in [('bim', bim, 10, 1, 0, 32), ('pgd', pgd, 20, 5, 2026, 16)]:
        results[name] = iterative_audit(folder, root)
        require(results[name]['result'] == 'FULL_OUTPUTS_CONSISTENT', name+' incomplete')
        settings = read(Path(folder)/'run.json')['settings']
        for key, value in dict(attack=name, steps=steps, restarts=restarts, seed=seed, batch_size=batch, step_size=.005).items():
            require(settings[key] == value, name+' setting: '+key)
    results['jsma'] = jsma_audit(jsma, root)
    require(results['jsma']['result'] == 'FULL_SAVED_EVIDENCE_CONSISTENT', 'JSMA incomplete')
    settings = read(Path(jsma)/'run.json')['settings']
    for key, value in dict(model='cnn', defense='none', theta=1., gamma=.01, max_steps=246, limit=781).items():
        require(settings[key] == value, 'JSMA setting: '+key)
    results['mobilenet'] = audit_mobile(training, evaluation, root)
    return {'result': 'FULL_SAVED_EVIDENCE_CONSISTENT', 'stages': results, 'recovery_source_commit': source,
            'gpu_execution_proven_by_this_audit': False,
            'note': 'Saved evidence only. Inspect GPU execution logs and source lineage separately before publication.',
            'independent_verification_approval': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('bim', 'pgd', 'jsma', 'training', 'evaluation'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(audit_all(**vars(args)), indent=2))


if __name__ == '__main__':
    main()
