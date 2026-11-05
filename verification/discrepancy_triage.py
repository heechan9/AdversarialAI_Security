"""Read-only investigation of saved external label discrepancies, not causal proof."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

try:
    from .status_registry import REGISTRY, build as build_status, read_evidence, read_json, require
except ImportError:
    from status_registry import REGISTRY, build as build_status, read_evidence, read_json, require

MODELS = ('cnn', 'mobilenet')
METHODS = ('gaussian', 'mean')
PIPELINES = ('clean', 'defended_clean', 'attacked', 'transfer_defended', 'adaptive_defended')
EPSILONS = ('0', '0.01', '0.03', '0.05')


def count(value, maximum):
    require(type(value) is int and 0 <= value <= maximum, 'invalid count')
    return value


def summarize(document, method, manifest, classes):
    """Validate row-level accounting before grouping any diagnostic records."""
    require(document.get('inference_performed') is False, 'not a saved-only diagnostic')
    cells = {}
    for condition in document['conditions']:
        name = condition['file']
        require(name not in cells, 'duplicate condition')
        cells[name] = condition
        count(condition['samples'], 781)
    expected = {f'{m}_eps_{e}_samples.csv': (m, e) for m in MODELS for e in EPSILONS}
    require(set(cells) == set(expected), 'condition coverage')
    required_hashes = {f'{side}/{name}' for side in ('reference', 'actual') for name in expected}
    hashes = document['input_sha256']
    require(set(hashes) == required_hashes, 'input hash coverage')
    require(all(isinstance(h, str) and re.fullmatch('[0-9a-f]{64}', h) for h in hashes.values()), 'invalid input hash')
    differences = []; seen = set(); counts = Counter(); gains = Counter(); losses = Counter()
    for d in document['differences']:
        name, pipeline = d['file'], d['pipeline']
        require(name in expected and pipeline in PIPELINES, 'unknown difference condition')
        row = count(d['row_index'], len(manifest)-1)
        require(d['relative_path'] == manifest[row]['relative_path'], 'row/path mismatch')
        require(all(type(d[k]) is str and d[k] in classes for k in ('reference', 'actual', 'true_index')), 'invalid label')
        require(classes[d['true_index']] == manifest[row]['label'], 'ground-truth mismatch')
        require(d['reference'] != d['actual'], 'not a difference')
        identity = (name, pipeline, row)
        require(identity not in seen, 'duplicate difference cell'); seen.add(identity)
        key = (name, pipeline); counts[key] += 1
        gained = d['actual'] == d['true_index']; lost = d['reference'] == d['true_index']
        gains[key] += gained; losses[key] += lost
        model, epsilon = expected[name]
        differences.append(dict(method=method, model=model, epsilon=epsilon, **d,
                                outcome='newly_correct' if gained else 'newly_incorrect' if lost else 'both_wrong',
                                reference_csv_sha256=hashes['reference/'+name],
                                actual_csv_sha256=hashes['actual/'+name]))
    require(document['unique_affected_images'] == len({d['relative_path'] for d in differences}), 'affected-image count mismatch')
    groups = []
    for name, (model, epsilon) in expected.items():
        c = cells[name]
        require(c['samples'] == len(manifest) == 781, 'sample coverage')
        require(set(c['pipelines']) == set(PIPELINES), 'pipeline coverage')
        for pipeline in PIPELINES:
            p = c['pipelines'][pipeline]; key = (name, pipeline)
            n = count(p['label_differences'], 781)
            ref = count(p['reference_correct'], 781); actual = count(p['actual_correct'], 781)
            require(n == counts[key], 'per-condition difference count mismatch')
            require(actual-ref == gains[key]-losses[key], 'accuracy delta does not reconcile')
            groups.append(dict(method=method, model=model, epsilon=epsilon, file=name, pipeline=pipeline,
                               compared_prediction_cells=781, differing_prediction_cells=n,
                               reference_correct=ref, actual_correct=actual,
                               newly_correct=gains[key], newly_incorrect=losses[key],
                               both_wrong=n-gains[key]-losses[key]))
    return groups, differences


def build(root, *, method=None, model=None, pipeline=None, relative_path=None):
    root = Path(root).resolve()
    for value, allowed in ((method, METHODS), (model, MODELS), (pipeline, PIPELINES)):
        require(value is None or value in allowed, 'unknown filter')
    # Keep the existing status and lifecycle gates, including future fixes, authoritative.
    status = build_status(root)
    registry_raw = (root/REGISTRY).read_bytes()
    registry = read_json(registry_raw)
    external = next(r for r in registry['records'] if r['id'] == 'external-01')
    manifest_raw = (root/'configs/test_manifest.json').read_bytes()
    manifest = read_json(manifest_raw)['test_files']
    classes_raw = (root/'configs/classes.json').read_bytes(); classes = read_json(classes_raw)
    require(set(classes) == {str(i) for i in range(10)} and len(set(classes.values())) == 10, 'class map')
    require(len(manifest) == 781 and len({m['relative_path'] for m in manifest}) == 781, 'manifest coverage')
    groups = []; cases = []; evidence = []
    for entry in sorted(external['evidence'], key=lambda e: e['path']):
        name = Path(entry['path']).name.removesuffix('_differences.json')
        require(name in METHODS, 'unknown method')
        document = read_evidence(root, entry)
        g, d = summarize(document, name, manifest, classes)
        groups.extend(g)
        cases.extend(dict(**item, evidence_path=entry['path'], evidence_sha256=entry['sha256'],
                          source_commit=document['source_commit']) for item in d)
        evidence.append(dict(**entry, source_commit=document['source_commit']))
    cases.sort(key=lambda d: (d['relative_path'], d['method'], d['file'], d['pipeline']))
    selected = [d for d in cases if all(v is None or d[k] == v for k, v in
                [('method', method), ('model', model), ('pipeline', pipeline), ('relative_path', relative_path)])]
    image_counts = Counter(d['relative_path'] for d in cases)
    return dict(schema_version=1, kind='saved_external_discrepancy_triage',
                inference_performed=False, independent_reproduction=False, cause_status=status['cause_status'],
                status_by_run={c['id']: c['status'] for c in status['cards']},
                discrepancy_state={i['id']: i['state'] for i in status['discrepancies']},
                source_evidence=evidence, registry_sha256=hashlib.sha256(registry_raw).hexdigest(),
                manifest_sha256=hashlib.sha256(manifest_raw).hexdigest(),
                classes_sha256=hashlib.sha256(classes_raw).hexdigest(),
                totals=dict(compared_prediction_cells=sum(g['compared_prediction_cells'] for g in groups),
                            differing_prediction_cells=len(cases), unique_affected_images=len(image_counts)),
                condition_groups=groups,
                affected_images=[dict(relative_path=p, differing_prediction_cells=n) for p, n in sorted(image_counts.items())],
                selection=dict(method=method, model=model, pipeline=pipeline, relative_path=relative_path,
                               differing_prediction_cells=len(selected),
                               unique_affected_images=len({d['relative_path'] for d in selected})),
                cases=selected,
                limitations=['Saved JSON accounting, not raw CSV re-audit or model re-inference.',
                             'Prediction cells repeat images across conditions; they are not independent samples.',
                             'Filters select case records only; totals and condition denominators remain unfiltered.',
                             'Frequency is an investigation aid, not severity, cause, or statistical significance.',
                             'Original training manifests remain unrecovered; this does not repair training provenance.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--method', choices=METHODS)
    parser.add_argument('--model', choices=MODELS)
    parser.add_argument('--pipeline', choices=PIPELINES)
    parser.add_argument('--relative-path', help='Exact saved image identifier; never opened as a filesystem path')
    args = parser.parse_args()
    try:
        result = build(args.repo_root, method=args.method, model=args.model,
                       pipeline=args.pipeline, relative_path=args.relative_path)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(2, f'Triage rejected: {exc}\n')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
