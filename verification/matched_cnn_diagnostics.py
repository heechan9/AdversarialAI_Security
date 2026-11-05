"""Trace classwise and paired errors in audited saved CNN predictions; no inference."""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'results/extensions/matched_cnn_20261024'
MODELS = ('baseline', 'clean_only', 'pgd_mixed')
CONDITIONS = ('clean', 'pgd7', 'pgd50')
OUTCOMES = ('changed', 'all', 'newly_correct', 'newly_incorrect', 'both_correct', 'both_wrong')
CASE_FIELDS = ('relative_path', 'true_index', 'true_class', 'condition', 'outcome',
               'baseline_clean_pred', 'baseline_condition_pred',
               'clean_only_clean_pred', 'clean_only_condition_pred',
               'pgd_mixed_clean_pred', 'pgd_mixed_condition_pred')


def saved_auditor():
    spec = importlib.util.spec_from_file_location(
        'matched_cnn_saved_audit', ROOT / 'verification/matched_cnn_saved_audit.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def describe(cases, condition):
    """All metrics use the selected class BEFORE the outcome filter."""
    n = len(cases)
    metrics = {}
    for model in MODELS:
        clean = sum(c[f'{model}_clean_pred'] == c['true_index'] for c in cases)
        correct = sum(c[f'{model}_condition_pred'] == c['true_index'] for c in cases)
        successes = None if condition == 'clean' else sum(
            c[f'{model}_clean_pred'] == c['true_index']
            and c[f'{model}_condition_pred'] != c['true_index'] for c in cases)
        metrics[model] = dict(samples=n, correct=correct,
            accuracy=correct / n if n else None, clean_correct=clean,
            own_clean_asr_successes=successes,
            own_clean_asr_denominator=None if condition == 'clean' else clean,
            own_clean_asr=successes / clean if successes is not None and clean else None)
    counts = {name: sum(c['outcome'] == name for c in cases)
              for name in OUTCOMES if name not in ('all', 'changed')}
    paired = dict(counts, net_correct=counts['newly_correct'] - counts['newly_incorrect'])
    common = [c for c in cases if all(c[f'{m}_clean_pred'] == c['true_index']
                                    for m in ('clean_only', 'pgd_mixed'))]
    common_asr = {'samples': len(common), 'models': {}}
    for model in ('clean_only', 'pgd_mixed'):
        successes = None if condition == 'clean' else sum(
            c[f'{model}_condition_pred'] != c['true_index'] for c in common)
        common_asr['models'][model] = dict(successes=successes,
            asr=successes / len(common) if successes is not None and common else None)
    return dict(samples=n, models=metrics, mixed_vs_clean_only=paired,
                common_clean_correct_asr=common_asr)


def matches(case, outcome):
    if outcome == 'all':
        return True
    if outcome == 'changed':
        return case['outcome'] in ('newly_correct', 'newly_incorrect')
    return case['outcome'] == outcome


def build_report(directory=DEFAULT, condition='pgd50', class_name=None, outcome='changed'):
    if condition not in CONDITIONS or outcome not in OUTCOMES:
        raise ValueError('Unknown condition or paired outcome')
    directory = Path(directory)
    auditor = saved_auditor()
    checked = auditor.audit(directory)  # Mandatory full saved-evidence gate; never bypassed.
    evaluation = auditor.read_json(directory / 'evaluation.json')
    classes = auditor.read_json(ROOT / 'configs/classes.json')
    labels = [classes[str(i)] for i in range(10)]
    if class_name is not None and class_name not in labels:
        raise ValueError('Unknown true class: ' + class_name)

    rows = {}
    hashes = {}
    for model in MODELS:
        path = directory / f'{model}.csv'
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != evaluation['models'][model]['csv_sha256']:
            raise ValueError('CSV changed after audit: ' + model)
        hashes[path.name] = digest
        parsed = csv.DictReader(io.StringIO(raw.decode('utf-8'), newline=''))
        rows[model] = {r['relative_path']: r for r in parsed}

    cases = []
    for identity, b in rows['clean_only'].items():
        true = int(b['true_index'])
        model_rows = {model: rows[model][identity] for model in MODELS}
        column = 'clean_pred' if condition == 'clean' else condition + '_pred'
        b_ok = int(b[column]) == true
        c_ok = int(model_rows['pgd_mixed'][column]) == true
        paired_outcome = ('both_correct' if b_ok and c_ok else
                          'both_wrong' if not b_ok and not c_ok else
                          'newly_correct' if c_ok else 'newly_incorrect')
        case = dict(relative_path=identity, true_index=true, true_class=classes[str(true)],
                    condition=condition, outcome=paired_outcome)
        for model, row in model_rows.items():
            case[f'{model}_clean_pred'] = int(row['clean_pred'])
            case[f'{model}_condition_pred'] = int(row[column])
        cases.append(case)
    # Identity order, labels and duplicates were checked by the original auditor.
    overall = describe(cases, condition)
    for model in MODELS:
        recorded = checked['models'][model][condition]
        metric = overall['models'][model]
        if metric['samples'] != recorded['samples'] or metric['correct'] != recorded['correct']:
            raise ValueError('Diagnostics differ from saved audit: ' + model)
        if condition != 'clean' and (
                metric['own_clean_asr_successes'] != recorded['asr_successes'] or
                metric['own_clean_asr_denominator'] != recorded['asr_denominator']):
            raise ValueError('ASR differs from saved audit: ' + model)
    paired = checked['mixed_minus_clean_only'][condition]
    if any(overall['mixed_vs_clean_only'][key] != paired[key]
           for key in ('newly_correct', 'newly_incorrect', 'net_correct')):
        raise ValueError('Paired outcomes differ from saved audit')

    selected = cases if class_name is None else [c for c in cases if c['true_class'] == class_name]
    exported = [c for c in selected if matches(c, outcome)]
    return dict(
        schema_version=1, status='SAVED_CNN_DIAGNOSTICS_NOT_INDEPENDENT_REPRODUCTION',
        evaluation_source_commit=evaluation['source_commit'],
        condition=condition, settings=evaluation['settings'],
        source_sha256=dict(hashes,
            **{'evaluation.json': hashlib.sha256((directory / 'evaluation.json').read_bytes()).hexdigest(),
               'classes.json': hashlib.sha256((ROOT / 'configs/classes.json').read_bytes()).hexdigest()}),
        selection=dict(true_class=class_name, outcome=outcome, exported_cases=len(exported),
            metrics_scope='All samples in the selected true class, before outcome filtering'),
        overall=overall, selected=describe(selected, condition),
        by_class=[dict(true_class=label, **describe(
            [c for c in cases if c['true_class'] == label], condition)) for label in labels],
        cases=exported,
        boundaries=dict(independent_verification_approval=False,
            existing_external_stage_b='FAIL', hyunsu_selected_diagnostic='INCOMPLETE',
            completed_training_seeds=[2026],
            historical_training_manifests_recovered=False,
            original_baseline_training_exposure_verified=False,
            whole_dataset_rights_verified=False, vessel_scene_independence_verified=False,
            statistical_inference_performed=False),
        notes=[
            'Saved predictions only; no inference, training or raw-image/model access.',
            'Paired by original image ID; each model used its own gradient and attack input.',
            'Own-clean ASR denominators are model-specific. Common-clean ASR uses only B/C clean-correct overlap.',
            'Class selection changes metric cohorts; outcome filtering changes exported cases only.',
            'Clean has no attack ASR; zero denominators are null, not zero success.',
            'Classwise and paired results are descriptive; no causal or independent-sample claim.',
        ])


def export_report(report, directory):
    """Create a new output directory. Existing files and evidence are never overwritten."""
    directory = Path(directory)
    json_bytes = (json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=CASE_FIELDS, lineterminator='\n')
    writer.writeheader()
    writer.writerows(report['cases'])
    csv_bytes = buffer.getvalue().encode('utf-8')
    directory.mkdir(parents=True, exist_ok=False)
    try:
        (directory / 'report.json').write_bytes(json_bytes)
        (directory / 'cases.csv').write_bytes(csv_bytes)
    except OSError:
        for name in ('report.json', 'cases.csv'):
            (directory / name).unlink(missing_ok=True)
        directory.rmdir()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=DEFAULT)
    parser.add_argument('--condition', choices=CONDITIONS, default='pgd50')
    parser.add_argument('--class-name', help='Exact true class label, e.g. Tug or Container Ship')
    parser.add_argument('--outcome', choices=OUTCOMES, default='changed')
    parser.add_argument('--output-dir', type=Path, help='New directory for report.json and cases.csv')
    args = parser.parse_args(argv)
    report = build_report(args.directory, args.condition, args.class_name, args.outcome)
    if args.output_dir is not None:
        export_report(report, args.output_dir)
        print(json.dumps(dict(status=report['status'], condition=report['condition'],
            selection=report['selection'], selected=report['selected'],
            output_directory=str(args.output_dir)), ensure_ascii=False, indent=2, allow_nan=False))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, csv.Error) as error:
        print('DIAGNOSTICS_BLOCKED: ' + str(error), file=sys.stderr)
        sys.exit(1)
