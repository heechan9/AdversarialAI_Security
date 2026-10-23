"""Descriptive, manifest-aligned defense transitions; no independence assumed."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path, PurePosixPath

PREDICTIONS = ('clean_pred', 'defended_clean_pred', 'attacked_pred',
               'transfer_defended_pred', 'adaptive_defended_pred')


def normalize(value):
    value = value.replace('\\', '/')
    if not value or value.startswith('/') or ':' in value or any(x in ('', '.', '..') for x in value.split('/')):
        raise ValueError('invalid relative path')
    return str(PurePosixPath(value))


def index_rows(rows):
    result = {}
    for row in rows:
        key = normalize(row['relative_path'])
        if key in result:
            raise ValueError('duplicate normalized image path')
        result[key] = row
    if not result:
        raise ValueError('empty rows')
    return result


def rate(n, d):
    return n / d if d else None


def transitions(a, b):
    if not a or len(a) != len(b):
        raise ValueError('paired outcomes must be nonempty and aligned')
    both = sum(x and y for x, y in zip(a, b))
    gained = sum(not x and y for x, y in zip(a, b))
    lost = sum(x and not y for x, y in zip(a, b))
    return {'n': len(a), 'a_correct': sum(a), 'b_correct': sum(b),
            'both_correct': both, 'both_wrong': len(a)-both-gained-lost,
            'gained': gained, 'lost': lost,
            'b_minus_a_percentage_points': 100*(gained-lost)/len(a)}


def summarize(rows):
    if not rows:
        raise ValueError('empty group')
    correct = {k: [r[k] == r['true_index'] for r in rows] for k in PREDICTIONS}
    clean, dc = correct['clean_pred'], correct['defended_clean_pred']
    plain, transfer, adaptive = (correct[k] for k in PREDICTIONS[2:])
    def asr(base, attacked):
        successes = sum(c and not a for c, a in zip(base, attacked))
        denominator = sum(base)
        return {'successes': successes, 'clean_correct_denominator': denominator,
                'asr': rate(successes, denominator)}
    common = [a and b for a, b in zip(clean, dc)]
    return {'n': len(rows),
            'clean_plain_to_defended': transitions(clean, dc),
            'attack_plain_to_transfer_defended': transitions(plain, transfer),
            'attack_plain_to_adaptive_defended': transitions(plain, adaptive),
            'defended_transfer_to_adaptive': transitions(transfer, adaptive),
            'asr_own_clean_sets_not_paired': {
                'plain': asr(clean, plain), 'transfer': asr(dc, transfer),
                'adaptive': asr(dc, adaptive)},
            'common_clean_correct_subset': {
                'n': sum(common), 'plain': asr(common, plain),
                'transfer': asr(common, transfer), 'adaptive': asr(common, adaptive)}}


def read_csv(path):
    with path.open(newline='') as handle:
        reader = csv.DictReader(handle)
        if len(reader.fieldnames or []) != len(set(reader.fieldnames or [])):
            raise ValueError('duplicate CSV headers')
        rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError('malformed CSV')
    return rows


def align(attack_rows, defense_rows, manifest, classes, epsilon):
    attack, defense = index_rows(attack_rows), index_rows(defense_rows)
    expected = index_rows(manifest['test_files'])
    if len(expected) != manifest['test_samples'] or set(attack) != set(expected) or set(defense) != set(expected):
        raise ValueError('manifest coverage differs')
    result = []
    for key in sorted(expected):
        a, d = attack[key], defense[key]
        for row in (a, d):
            ep = float(row['epsilon'])
            if not math.isfinite(ep) or ep != epsilon:
                raise ValueError('epsilon mismatch/nonfinite')
            if row['true_index'] not in classes or classes[row['true_index']] != expected[key]['label']:
                raise ValueError('manifest truth mismatch')
        if a['true_index'] != d['true_index']:
            raise ValueError('truth mismatch')
        if a['clean_predicted_index'] != d['clean_pred'] or a['adversarial_predicted_index'] != d['attacked_pred']:
            raise ValueError('unpaired baseline predictions')
        if any(d[k] not in classes for k in PREDICTIONS):
            raise ValueError('invalid predicted class')
        for k in ('original_linf', 'adaptive_linf'):
            value = float(d[k])
            if not math.isfinite(value) or not 0 <= value <= epsilon + 1e-6:
                raise ValueError('invalid perturbation budget')
        if epsilon == 0 and (d['clean_pred'] != d['attacked_pred'] or d['defended_clean_pred'] != d['transfer_defended_pred'] or d['defended_clean_pred'] != d['adaptive_defended_pred']):
            raise ValueError('zero-budget identity violated')
        result.append(dict(d, relative_path=key, true_label=classes[d['true_index']]))
    return result


def review(root, pin):
    evidence = []
    for entry in pin['files']:
        data = (root / entry['path']).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != entry['git_blob_sha1']:
            raise ValueError('source pin mismatch: ' + entry['path'])
        evidence.append(dict(entry, sha256=hashlib.sha256(data).hexdigest()))
    manifest = json.loads((root/'configs/test_manifest.json').read_text())
    classes = json.loads((root/'configs/classes.json').read_text())
    conditions = []
    for model in ('cnn', 'mobilenet'):
        for ep in ('0', '0.01', '0.03', '0.05'):
            attacks = read_csv(root/f'results/attacks/provisional/fgsm_{model}_eps_{ep}_samples.csv')
            for defense in ('gaussian', 'mean'):
                defended = read_csv(root/f'results/defenses/experimental/{defense}_run_01/{model}_eps_{ep}_samples.csv')
                rows = align(attacks, defended, manifest, classes, float(ep))
                groups = {label: summarize([r for r in rows if r['true_label'] == label]) for label in classes.values()}
                conditions.append({'model': model, 'epsilon': float(ep), 'defense': defense,
                                   'overall': summarize(rows), 'by_class': groups})
    return {'source_head': pin['source_head'], 'status': 'DESCRIPTIVE_SAVED_PREDICTIONS_ONLY',
            'independent_units_verified': False,
            'inference': {'mcnemar_p': None, 'bootstrap_ci': None,
                          'reason': 'No verified scene/vessel/session grouping or independent sampling design. Image paths and byte hashes do not establish independence.'},
            'limitations': ['Same 781 images recur across conditions; do not pool as independent observations.',
                            'Transfer and adaptive use different attack constructions; this is not an equal-perturbation defense treatment effect.',
                            'Own-clean ASRs have different eligibility sets; only the explicitly named common-clean subset is aligned.',
                            'No new inference, training, image/model byte verification, independent reproduction or robustness gain.'],
            'input_evidence': evidence, 'conditions': conditions}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    result = review(here.parents[1], json.loads((here/'source_pin.json').read_text()))
    with args.output.open('x') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write('\n')
