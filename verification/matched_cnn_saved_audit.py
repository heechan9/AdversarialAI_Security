"""Recalculate saved matched-CNN evidence. No inference or independent approval."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'results/extensions/matched_cnn_20261024'
PIN = 'db3bfe6b79d3cecb2ef57aeaaf29ab9d89b5d9bf'
MODELS = ('baseline', 'clean_only', 'pgd_mixed')
FIELDS = ['relative_path', 'true_index', 'clean_pred', 'pgd7_pred',
          'pgd50_pred', 'pgd7_linf', 'pgd50_linf']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result

    def invalid(value):
        raise ValueError('Nonfinite JSON: ' + value)

    return json.loads(path.read_text(encoding='utf-8'),
                      object_pairs_hook=unique, parse_constant=invalid)


def close(actual, expected, label):
    require(type(expected) in (int, float) and math.isfinite(expected)
            and abs(actual - expected) < 1e-12, 'Metric mismatch: ' + label)


def audit(directory=DEFAULT):
    directory = Path(directory)
    index = read_json(directory / 'evidence-index.json')
    for relative, entry in index['files'].items():
        path = directory / relative
        require(not Path(relative).is_absolute() and '..' not in Path(relative).parts,
                'Invalid indexed path')
        require(path.is_file() and not path.is_symlink(), 'Missing/nonregular evidence: ' + relative)
        require(sha(path) == entry['sha256'], 'Indexed SHA mismatch: ' + relative)
    report = read_json(directory / 'evaluation.json')
    paired = read_json(directory / 'paired-audit.json')
    require(report['status'] == 'COMPLETED_NOT_INDEPENDENT_APPROVAL', 'Incomplete evaluation')
    require(report['source_commit'] == PIN, 'Unexpected source revision')
    require(report['independent_verification_approval'] is False, 'Approval boundary changed')
    require(report['paired_audit'] == paired, 'Embedded paired audit differs')
    require(paired['result'] == 'PAIRED_RECORDED_PROTOCOL_AND_CHECKPOINTS_CONSISTENT', 'Pair audit failed')
    require(paired['independent_verification_approval'] is False
            and paired['test_evaluation_complete'] is False, 'Pre-inference audit changed')
    require(report['settings'] == dict(seed=2026, batch_size=8, epsilon=.03, step_size=.005,
            pgd7=dict(steps=7, restarts=1), pgd50=dict(steps=50, restarts=5)), 'Evaluation settings differ')
    require(set(report['models']) == set(MODELS), 'Three model results required')
    require(sha(directory / 'provenance/executed-evaluator-v2.py') == report['evaluator_sha256'],
            'Executed evaluator differs')
    manifest_path = ROOT / 'configs/test_manifest.json'
    require(sha(manifest_path) == report['test_manifest_sha256'], 'Test manifest differs')
    manifest = read_json(manifest_path)
    classes = read_json(ROOT / 'configs/classes.json')
    class_index = {value: int(key) for key, value in classes.items()}
    identities = [(item['relative_path'], class_index[item['label']]) for item in manifest['test_files']]
    require(len(identities) == len(set(identities)) == manifest['test_samples'] == 781,
            'Canonical test identities invalid')
    require(report['baseline_sha256'] == next(item['sha256'] for item in manifest['models']
            if item['path'] == 'models/cnn_baseline.h5'), 'Baseline identity differs')

    training = {}
    for mode, weight in (('clean_only', 1.0), ('pgd_mixed', .5)):
        record = read_json(directory / ('provenance/training-' + mode + '.json'))
        training[mode] = record
        require(record['status'] == 'TRAINED_NOT_TEST_EVALUATED', 'Training snapshot status differs')
        require(record['source_commit'] == PIN and record['source_model_sha256'] == report['baseline_sha256'],
                'Training source/initialization differs')
        require(record['training_mode'] == record['settings']['training_mode'] == mode
                and record['clean_weight'] == weight, 'Training arm differs')
        protocol = record['comparison_protocol']
        digest = hashlib.sha256(json.dumps(protocol, sort_keys=True, separators=(',', ':'),
                                allow_nan=False).encode()).hexdigest()
        require(digest == record['comparison_protocol_sha256'] == paired['comparison_protocol_sha256'],
                'Recorded protocol hash differs')
        require(record['trained_model_sha256'] == paired['model_sha256'][mode]
                == report['models'][mode]['model_sha256'], 'Selected checkpoint metadata differs')
        require(protocol['source_commit'] == PIN and protocol['source_model_sha256'] == report['baseline_sha256']
                and protocol['split_audit_sha256'] == record['split_audit_sha256'], 'Protocol identity differs')
        require(protocol['settings'] == {key: record['settings'][key] for key in protocol['settings']},
                'Training settings/protocol differ')
        epochs = record['epochs']
        require([epoch['epoch'] for epoch in epochs] == [1, 2, 3]
                and all(epoch['validation_samples'] == 689 for epoch in epochs), 'Incomplete training epochs')
        selected = max(epochs, key=lambda epoch: (epoch['validation_pgd_accuracy'], -epoch['epoch']))
        require(selected['epoch'] == record['best_epoch'], 'Checkpoint selection differs')
    require(training['clean_only']['comparison_protocol'] == training['pgd_mixed']['comparison_protocol'],
            'Training protocols differ')

    rows_by_model, metrics = {}, {}
    for name in MODELS:
        result = report['models'][name]
        require(result['csv'] == name + '.csv' and type(result['samples']) is int
                and result['samples'] == 781, 'Incomplete/wrong model CSV')
        path = directory / (name + '.csv')
        require(sha(path) == result['csv_sha256'], 'CSV SHA mismatch: ' + name)
        with path.open(newline='', encoding='utf-8') as stream:
            reader = csv.DictReader(stream, strict=True)
            require(reader.fieldnames == FIELDS, 'CSV schema differs')
            raw = list(reader)
        require(len(raw) == 781, 'CSV row count differs')
        rows = []
        for row in raw:
            require(set(row) == set(FIELDS) and all(value is not None for value in row.values()),
                    'Ragged CSV row')
            for key in ('true_index', 'clean_pred', 'pgd7_pred', 'pgd50_pred'):
                value = int(row[key])
                require(str(value) == row[key] and 0 <= value < 10, 'Invalid class index')
                row[key] = value
            for key in ('pgd7_linf', 'pgd50_linf'):
                value = float(row[key])
                require(math.isfinite(value) and 0 <= value <= .030001, 'Invalid perturbation record')
            rows.append(row)
        require([(r['relative_path'], r['true_index']) for r in rows] == identities,
                'Test identity/order/label differs: ' + name)
        clean_n = sum(r['clean_pred'] == r['true_index'] for r in rows)
        close(clean_n / 781, result['clean_accuracy'], name + '/clean')
        calculated = {'clean': {'correct': clean_n, 'samples': 781, 'accuracy': clean_n / 781}}
        for attack in ('pgd7', 'pgd50'):
            correct = sum(r[attack + '_pred'] == r['true_index'] for r in rows)
            successes = sum(r['clean_pred'] == r['true_index']
                            and r[attack + '_pred'] != r['true_index'] for r in rows)
            recorded = result['attacks'][attack]
            close(correct / 781, recorded['accuracy'], name + '/' + attack)
            close(successes / clean_n, recorded['asr'], name + '/' + attack + '/asr')
            require(recorded['asr_successes'] == successes and recorded['asr_denominator'] == clean_n,
                    'ASR counts differ')
            calculated[attack] = dict(correct=correct, samples=781, accuracy=correct / 781,
                                      asr_successes=successes, asr_denominator=clean_n)
        require(all(not (r['pgd7_pred'] != r['true_index'] and r['pgd50_pred'] == r['true_index'])
                    for r in rows), 'Stronger-attack success containment differs')
        rows_by_model[name], metrics[name] = rows, calculated

    differences = {}
    for condition, column in (('clean', 'clean_pred'), ('pgd7', 'pgd7_pred'), ('pgd50', 'pgd50_pred')):
        gained = lost = 0
        for first, second in zip(rows_by_model['clean_only'], rows_by_model['pgd_mixed']):
            a, b = first[column] == first['true_index'], second[column] == second['true_index']
            gained += b and not a
            lost += a and not b
        differences[condition] = dict(newly_correct=gained, newly_incorrect=lost,
                net_correct=gained - lost, percentage_points=(gained - lost) / 781 * 100)
    return dict(status='SAVED_EVIDENCE_CONSISTENT_NOT_INDEPENDENT_REPRODUCTION',
                seed=2026, samples_per_model=781, models=metrics,
                mixed_minus_clean_only=differences, independent_verification_approval=False,
                scope='Saved bytes, recorded identities, labels and metrics only; no model/split byte recheck or inference.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path, nargs='?', default=DEFAULT)
    args = parser.parse_args()
    print(json.dumps(audit(args.directory), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
