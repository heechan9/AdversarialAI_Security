"""Actual auditor outputs over temporary copies of public evidence, no inference."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[3])
root = parser.parse_args().repo_root.resolve()
sys.path.insert(0, str(root))
from verification.fgsm_run_audit import audit, audit_condition, read_json, sha

epsilons = [0., .01, .03, .05]
manifest = read_json(root / 'configs/test_manifest.json')
classes = read_json(root / 'configs/classes.json')


def invocation(parent, model, saved, recorded, status):
    output = parent / model
    output.mkdir()
    for epsilon in saved:
        for suffix in ('samples.csv', 'report.json', 'confusion_matrix.csv', 'confusion_matrix.png'):
            name = f'fgsm_{model}_eps_{epsilon:g}_{suffix}'
            shutil.copyfile(root / 'results/attacks/provisional' / name, output / name)
    if status is None:
        return output
    model_path = 'models/cnn_baseline.h5' if model == 'cnn' else 'models/mobilenet_finetuned.h5'
    journal = dict(schema_version=1, kind='fgsm_evaluation_progress', model=model,
                   independent_verification_approval=False, status=status, epsilons=epsilons,
                   conditions=[], run_id='synthetic-web-regression',
                   error='RuntimeError: synthetic regression error',
                   model_sha256=next(v['sha256'] for v in manifest['models'] if v['path'] == model_path),
                   manifest_sha256=sha(root / 'configs/test_manifest.json'),
                   classes_sha256=sha(root / 'configs/classes.json'))
    for epsilon in recorded:
        metrics, _ = audit_condition(output / f'fgsm_{model}_eps_{epsilon:g}_samples.csv', epsilon, manifest, classes)
        journal['conditions'].append(dict(epsilon=epsilon, samples=781, summary=metrics,
            artifact_sha256={p.name: sha(p) for p in output.glob(f'fgsm_{model}_eps_{epsilon:g}_*')}))
    if status == 'COMPLETED_REQUESTED_SCOPE':
        for name in (f'fgsm_{model}.csv', f'fgsm_{model}_metadata.json'):
            shutil.copyfile(root / 'results/attacks/provisional' / name, output / name)
        metadata = read_json(output / f'fgsm_{model}_metadata.json')
        journal.update({key: metadata[key] for key in ('python', 'tensorflow', 'keras', 'input_size')})
        journal['artifact_sha256'] = {p.name: sha(p) for p in output.glob(f'fgsm_{model}*')}
    (output / f'fgsm_{model}_execution.json').write_text(json.dumps(journal), encoding='utf-8')
    return output


reports = {'public': audit([root / 'results/attacks/provisional'], root)}
with tempfile.TemporaryDirectory(prefix='paulguard-web-regression-') as temporary:
    parent = Path(temporary)
    for name, saved, recorded, status in [
        ('partial', epsilons[:2], [], None),
        ('interrupted', epsilons[:2], epsilons[:2], 'INTERRUPTED'),
        ('orphan', epsilons[:3], epsilons[:2], 'RUNNING'),
        ('error', epsilons, epsilons, 'ERROR'),
        ('empty_error', [], [], 'ERROR'),
        ('preparing', [], [], 'PREPARING'),
        ('completed', epsilons, epsilons, 'COMPLETED_REQUESTED_SCOPE'),
    ]:
        folder = parent / name
        folder.mkdir()
        output = invocation(folder, 'mobilenet', saved, recorded, status)
        reports[name] = audit([output], root, ['mobilenet'])
        if name == 'error':
            reports['selected_error'] = audit([output], root, ['mobilenet'], [.05, .01])
    folder = parent / 'split'
    folder.mkdir()
    cnn = invocation(folder, 'cnn', epsilons, [], None)
    mobile = invocation(folder, 'mobilenet', epsilons[:2], epsilons[:2], 'INTERRUPTED')
    reports['split'] = audit([cnn, mobile], root)

print(json.dumps(reports, allow_nan=False))
