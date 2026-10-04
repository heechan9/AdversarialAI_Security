"""Read-only exhaustive label diagnostics; never replaces the Stage B verdict."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

PREDICTIONS = ('clean', 'defended_clean', 'attacked', 'transfer_defended', 'adaptive_defended')
COLUMNS = ['relative_path', 'epsilon', 'true_index'] + [p+'_pred' for p in PREDICTIONS] + ['original_linf', 'adaptive_linf']


def rows(path, epsilon):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f'{path.name}: invalid columns')
        result = list(reader)
    if len(result) != 781:
        raise ValueError(f'{path.name}: expected 781 rows')
    seen = set()
    for row in result:
        name = row['relative_path'].replace('\\', '/')
        if not name or name in seen or None in row or any(v is None for v in row.values()):
            raise ValueError('invalid/duplicate row')
        seen.add(name)
        row['relative_path'] = name
        for key in ['true_index'] + [p+'_pred' for p in PREDICTIONS]:
            if row[key] not in {str(i) for i in range(10)}:
                raise ValueError('invalid class index')
        if float(row['epsilon']) != epsilon:
            raise ValueError('epsilon mismatch')
        for key in ['original_linf', 'adaptive_linf']:
            value = float(row[key])
            if not math.isfinite(value) or not 0 <= value <= epsilon+1e-6:
                raise ValueError('invalid perturbation')
    return result


def compare(reference, actual):
    report = {'kind': 'saved_label_diagnostic_not_stage_b_approval', 'inference_performed': False,
              'conditions': [], 'differences': [], 'input_sha256': {}}
    for model in ('cnn', 'mobilenet'):
        for epsilon in (0., .01, .03, .05):
            name = f'{model}_eps_{epsilon:g}_samples.csv'
            a, b = rows(reference/name, epsilon), rows(actual/name, epsilon)
            for tag, root in [('reference', reference), ('actual', actual)]:
                report['input_sha256'][tag+'/'+name] = hashlib.sha256((root/name).read_bytes()).hexdigest()
            if [(r['relative_path'],r['true_index']) for r in a] != [(r['relative_path'],r['true_index']) for r in b]:
                raise ValueError(f'{name}: path/order/ground-truth mismatch')
            condition = {'file': name, 'samples': 781, 'pipelines': {}}
            for pred in PREDICTIONS:
                key = pred+'_pred'
                differences = [{'file': name, 'row_index': i, 'relative_path': r['relative_path'],
                                'pipeline': pred, 'reference': l[key], 'actual': r[key],
                                'true_index': r['true_index']}
                               for i,(l,r) in enumerate(zip(a,b)) if l[key] != r[key]]
                report['differences'].extend(differences)
                condition['pipelines'][pred] = {'label_differences': len(differences),
                    'reference_correct': sum(r[key]==r['true_index'] for r in a),
                    'actual_correct': sum(r[key]==r['true_index'] for r in b)}
            report['conditions'].append(condition)
    report['label_status'] = 'MISMATCH' if report['differences'] else 'MATCH'
    report['unique_affected_images'] = len({d['relative_path'] for d in report['differences']})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--actual', type=Path, required=True)
    args = parser.parse_args()
    report = compare(args.reference, args.actual)
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    raise SystemExit(1 if report['differences'] else 0)

if __name__ == '__main__':
    main()
