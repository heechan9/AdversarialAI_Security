"""Read-only FGSM completeness audit and fresh-directory resume plan.

This checks saved sample rows, aggregates, and available progress provenance. It
never infers process liveness, reruns models, edits status, or approves Stage B.
Legacy partial files lack execution provenance and cannot be silently adopted.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

FIELDS = ['relative_path', 'epsilon', 'true_index', 'true_label',
          'clean_predicted_index', 'clean_predicted_label',
          'adversarial_predicted_index', 'adversarial_predicted_label',
          'clean_correct', 'attack_success', 'linf']
MODELS = {'cnn': 'models/cnn_baseline.h5', 'mobilenet': 'models/mobilenet_finetuned.h5'}
DEFAULT_EPSILONS = (0., .01, .03, .05)


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f'nonfinite JSON: {value}')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'),
                      object_pairs_hook=unique, parse_constant=invalid)


def read_csv(path):
    require(not path.is_symlink(), f'CSV symlink forbidden: {path.name}')
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, strict=True)
        fields = reader.fieldnames
        require(fields and len(set(fields)) == len(fields), f'missing/duplicate CSV columns: {path.name}')
        rows = list(reader)
        require(all(None not in row and all(v is not None for v in row.values()) for row in rows),
                f'invalid CSV row width: {path.name}')
    return fields, rows


def audit_condition(path, epsilon, manifest, classes):
    fields, rows = read_csv(path)
    require(fields == FIELDS, f'sample schema mismatch: {path.name}')
    expected = manifest['test_files']
    require(len(rows) == len(expected) == manifest['test_samples'] == 781, f'incomplete sample rows: {path.name}')
    require(len({r['relative_path'] for r in expected}) == 781, 'duplicate manifest paths')
    true, clean, attacked, linf = [], [], [], []
    for index, (row, entry) in enumerate(zip(rows, expected)):
        where = f'{path.name}/{index}'
        require(row['relative_path'].replace('\\', '/') == entry['relative_path'], f'sample order/path mismatch: {where}')
        require(float(row['epsilon']) == epsilon, f'epsilon mismatch: {where}')
        indices = []
        for prefix in ('true', 'clean_predicted', 'adversarial_predicted'):
            value = row[prefix + '_index']
            require(value in classes, f'invalid class index: {where}/{prefix}')
            require(row[prefix + '_label'] == classes[value], f'class label mismatch: {where}/{prefix}')
            indices.append(int(value))
        t, c, a = indices
        require(row['true_label'] == entry['label'] == entry['relative_path'].split('/')[0], f'true label mismatch: {where}')
        require(row['clean_correct'] == str(c == t), f'clean-correct flag mismatch: {where}')
        require(row['attack_success'] == str(c == t and a != t), f'attack-success flag mismatch: {where}')
        value = float(row['linf'])
        require(math.isfinite(value) and 0 <= value <= epsilon + 1e-6, f'invalid perturbation: {where}')
        if epsilon == 0:
            require(value == 0 and c == a, f'epsilon-zero invariant failed: {where}')
        true.append(t); clean.append(c); attacked.append(a); linf.append(value)
    count = len(rows)
    den = sum(t == c for t, c in zip(true, clean))
    successes = sum(t == c and a != t for t, c, a in zip(true, clean, attacked))
    correct = sum(t == a for t, a in zip(true, attacked))
    f1 = []
    for label in sorted(set(true) | set(attacked)):
        tp = sum(t == a == label for t, a in zip(true, attacked))
        denominator = sum(t == label for t in true) + sum(a == label for a in attacked)
        f1.append(2 * tp / denominator if denominator else 0.)
    metrics = dict(epsilon=epsilon, test_samples=count, clean_accuracy=den/count,
        robust_accuracy=correct/count, accuracy_drop=den/count-correct/count,
        macro_f1=sum(f1)/len(f1), untargeted_asr=successes/den if den else None,
        attack_successes=successes, asr_denominator_clean_correct=den,
        linf_max=max(linf), linf_mean=sum(linf)/count)
    return metrics, clean


def compare_metrics(actual, expected, context):
    require(set(actual) == set(expected), f'summary schema mismatch: {context}')
    for key, value in expected.items():
        if value is None:
            require(actual[key] is None, f'summary metric mismatch: {context}/{key}')
        else:
            other = actual[key]
            require(not isinstance(other, bool), f'boolean summary metric: {context}/{key}')
            other = float(other)
            # The evaluator summarizes float32 linf arrays before CSV decimal serialization.
            tolerance = 5e-10 if key in ('linf_max', 'linf_mean') else 1e-12
            require(math.isfinite(other) and abs(other-value) <= tolerance, f'summary metric mismatch: {context}/{key}')


def validate_epsilons(values):
    require(isinstance(values, (list, tuple)) and bool(values), 'empty/invalid epsilon scope')
    require(all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in values), 'invalid epsilon scope')
    values = [0.0 if v == 0 else float(v) for v in values]
    require(len({f'{v:g}' for v in values}) == len(values), 'duplicate/colliding epsilon scope')
    return list(values)


def check_hashes(directory, hashes):
    require(isinstance(hashes, dict) and bool(hashes), 'empty artifact hashes')
    for name, digest in hashes.items():
        require(isinstance(name, str) and Path(name).name == name and '/' not in name and '\\' not in name,
                'unsafe artifact name')
        path = directory / name
        require(not path.is_symlink() and path.is_file(), f'missing/unsafe artifact: {name}')
        require(sha(path) == digest, f'artifact hash mismatch: {name}')


def audit(run_dirs, repo_root, models=('cnn', 'mobilenet'), epsilons=DEFAULT_EPSILONS):
    root = Path(repo_root)
    manifest_path, classes_path = root/'configs/test_manifest.json', root/'configs/classes.json'
    manifest, classes = read_json(manifest_path), read_json(classes_path)
    require(set(classes) == {str(i) for i in range(10)} and len(set(classes.values())) == 10,
            'invalid ten-class map')
    require(models and len(set(models)) == len(models) and set(models) <= set(MODELS), 'invalid model scope')
    epsilons = validate_epsilons(epsilons)
    directories = [Path(d).absolute() for d in run_dirs]
    require(directories and len(set(d.resolve() for d in directories)) == len(directories), 'duplicate/empty run directories')
    for directory in directories:
        require(directory.is_dir() and not any(p.is_symlink() for p in (directory, *directory.parents)),
                'run directory must exist without symlinks')
    model_hashes = {m: next(r['sha256'] for r in manifest['models'] if r['path'] == MODELS[m]) for m in models}
    conditions, missing, invocations = [], [], []
    rerun_conditions, execution_errors = [], []
    clean_reference = {}
    for model in models:
        for epsilon in epsilons:
            name = f'fgsm_{model}_eps_{epsilon:g}_samples.csv'
            candidates = [d/name for d in directories if (d/name).exists() or (d/name).is_symlink()]
            require(len(candidates) <= 1, f'ambiguous duplicate condition: {name}')
            if not candidates:
                missing.append(dict(model=model, epsilon=epsilon))
                continue
            path = candidates[0]
            metrics, clean = audit_condition(path, epsilon, manifest, classes)
            require(model not in clean_reference or clean_reference[model] == clean,
                    f'clean predictions differ between conditions: {model}')
            clean_reference[model] = clean
            item = dict(model=model, epsilon=epsilon, rows=781, file=str(path), sha256=sha(path), metrics=metrics)
            conditions.append(item)
    # Validate each invocation's own declared scope, not just the selected rows.
    for directory in directories:
        for model in models:
            metadata_path = directory/f'fgsm_{model}_metadata.json'
            aggregate_path = directory/f'fgsm_{model}.csv'
            journal_path = directory/f'fgsm_{model}_execution.json'
            local = [v for v in conditions if v['model'] == model and Path(v['file']).parent == directory]
            if not local and not any(p.exists() or p.is_symlink() for p in (metadata_path, aggregate_path, journal_path)):
                continue
            invocation = dict(directory=str(directory), model=model, provenance='LEGACY_EXECUTION_PROVENANCE_UNVERIFIED',
                              journal_status=None, completion_record_consistent=False)
            metadata = None
            if metadata_path.exists() or metadata_path.is_symlink():
                require(not metadata_path.is_symlink(), 'metadata symlink forbidden')
                metadata = read_json(metadata_path)
                require(metadata['model'] == model and metadata['model_sha256'] == model_hashes[model], 'metadata model identity mismatch')
                scope = validate_epsilons(metadata['epsilons'])
                require(metadata['input_size'] == ([128,128,3] if model == 'cnn' else [224,224,3]), 'metadata input size mismatch')
                require(metadata['input_range'] == [0,1] and metadata['norm'] == 'L-infinity', 'metadata input/attack scope mismatch')
                require(metadata['attack'] == 'untargeted FGSM, exactly one step' and metadata['loss'] == 'categorical_crossentropy'
                        and type(metadata['from_logits']) is bool and metadata['asr_denominator'] == 'clean-correct samples only',
                        'metadata attack/loss/ASR scope mismatch')
                require(aggregate_path.is_file(), 'metadata exists without aggregate CSV')
                _, aggregate = read_csv(aggregate_path)
                require(len(aggregate) == len(scope), 'aggregate epsilon coverage mismatch')
                require([float(r['epsilon']) for r in aggregate] == scope, 'aggregate epsilon order mismatch')
                for row, epsilon in zip(aggregate, scope):
                    name = f'fgsm_{model}_eps_{epsilon:g}_samples.csv'
                    metrics, clean = audit_condition(directory/name, epsilon, manifest, classes)
                    compare_metrics(row, metrics, name)
                    require(model not in clean_reference or clean_reference[model] == clean,
                            f'clean predictions differ between conditions: {model}')
                    clean_reference[model] = clean
            elif aggregate_path.exists():
                # Aggregate may be written just before interruption; it is never a completion marker.
                _, aggregate = read_csv(aggregate_path)
                scope = validate_epsilons([float(r['epsilon']) for r in aggregate])
                for row, epsilon in zip(aggregate, scope):
                    metrics, clean = audit_condition(directory/f'fgsm_{model}_eps_{epsilon:g}_samples.csv', epsilon, manifest, classes)
                    require(model not in clean_reference or clean_reference[model] == clean,
                            f'clean predictions differ between conditions: {model}')
                    clean_reference[model] = clean
                    compare_metrics(row, metrics, str(aggregate_path))
            if journal_path.exists() or journal_path.is_symlink():
                require(not journal_path.is_symlink(), 'journal symlink forbidden')
                journal = read_json(journal_path)
                require(journal['schema_version'] == 1 and journal['kind'] == 'fgsm_evaluation_progress' and journal['model'] == model,
                        'invalid execution journal')
                require(journal['independent_verification_approval'] is False, 'independent approval prohibited')
                require(journal['status'] in ('PREPARING','RUNNING','ERROR','INTERRUPTED','COMPLETED_REQUESTED_SCOPE'), 'invalid execution status')
                scope = validate_epsilons(journal['epsilons'])
                recorded = journal['conditions']
                seen = []
                if recorded or journal['status'] == 'COMPLETED_REQUESTED_SCOPE':
                    require(journal['model_sha256'] == model_hashes[model], 'journal model identity mismatch')
                    require(journal['manifest_sha256'] == sha(manifest_path) and journal['classes_sha256'] == sha(classes_path),
                            'journal input identity mismatch')
                for condition in recorded:
                    epsilon = condition['epsilon']
                    require(type(epsilon) in (int, float) and epsilon in scope and epsilon not in seen, 'duplicate/unexpected journal condition')
                    seen.append(epsilon)
                    name = f'fgsm_{model}_eps_{epsilon:g}_samples.csv'
                    required = {f'fgsm_{model}_eps_{epsilon:g}_{suffix}' for suffix in
                                ('samples.csv','report.json','confusion_matrix.csv','confusion_matrix.png')}
                    require(set(condition['artifact_sha256']) == required, 'incomplete condition artifact hashes')
                    check_hashes(directory, condition['artifact_sha256'])
                    metrics, clean = audit_condition(directory/name, epsilon, manifest, classes)
                    require(model not in clean_reference or clean_reference[model] == clean,
                            f'clean predictions differ between conditions: {model}')
                    clean_reference[model] = clean
                    require(condition['samples'] == 781, 'journal sample count mismatch')
                    compare_metrics(condition['summary'], metrics, name)
                unrecorded = [v['epsilon'] for v in local if v['epsilon'] not in seen]
                for item in local:
                    if journal['status'] == 'ERROR' or item['epsilon'] in unrecorded:
                        rerun_conditions.append(dict(
                            model=model, epsilon=item['epsilon'],
                            reason='RECORDED_EXECUTION_ERROR' if journal['status'] == 'ERROR'
                                   else 'SAVED_CONDITION_NOT_IN_JOURNAL'))
                if journal['status'] == 'ERROR':
                    execution_errors.append(dict(model=model, directory=str(directory),
                                                 run_id=journal['run_id'], error=journal.get('error')))
                invocation.update(
                    validated_recorded_epsilons=seen, unrecorded_saved_epsilons=unrecorded,
                    provenance='RECORDED_JOURNAL_INPUTS_AND_ARTIFACTS_VALIDATED' if recorded else 'JOURNAL_WITHOUT_COMPLETED_CONDITIONS',
                    journal_status=journal['status'], requested_epsilons=scope,
                    run_id=journal['run_id'], source_commit=journal.get('source_commit'), source_dirty=journal.get('source_dirty'),
                    recorded_runtime={key: journal.get(key) for key in
                                      ('python','platform','tensorflow','keras','numpy','numerical_environment')})
                if journal['status'] == 'ERROR':
                    invocation['provenance'] = 'RECORDED_ERROR_ARTIFACTS_ONLY'
                elif unrecorded:
                    invocation['provenance'] = 'JOURNAL_WITH_UNRECORDED_SAVED_CONDITIONS'
                if journal['status'] == 'COMPLETED_REQUESTED_SCOPE':
                    require(seen == scope and metadata is not None and metadata['epsilons'] == scope, 'completed journal missing requested conditions/metadata')
                    for key in ('python','tensorflow','keras','input_size'):
                        require(metadata[key] == journal[key], f'journal/metadata mismatch: {key}')
                    required = {f'fgsm_{model}.csv', f'fgsm_{model}_metadata.json'}
                    for condition in recorded:
                        required.update(condition['artifact_sha256'])
                    require(set(journal['artifact_sha256']) == required, 'completed journal artifact coverage mismatch')
                    check_hashes(directory, journal['artifact_sha256'])
                    invocation['completion_record_consistent'] = True
            invocations.append(invocation)
    saved_coverage = 'PARTIAL_SAVED_SAMPLE_COVERAGE' if missing else 'FULL_REQUESTED_SAVED_SAMPLE_COVERAGE'
    restart = {(v['model'], v['epsilon']) for v in missing + rerun_conditions}
    return dict(kind='fgsm_saved_output_audit',
        result=('RECORDED_EXECUTION_ERROR' if execution_errors else
                'SAVED_CONDITIONS_REQUIRE_RERUN' if rerun_conditions else saved_coverage),
        saved_sample_coverage=saved_coverage, execution_errors=execution_errors,
        rerun_conditions=rerun_conditions, resume_requires_error_resolution=bool(execution_errors),
        expected_conditions=len(models)*len(epsilons), checked_conditions=len(conditions),
        conditions=conditions, missing_conditions=missing, invocations=invocations,
        resume_plan=[dict(model=model, epsilons=[e for e in epsilons if (model, e) in restart],
                         output_requirement='NEW_DIRECTORY_OUTSIDE_ALL_PRIOR_OUTPUTS') for model in models
                     if any(m == model for m, e in restart)],
        independent_verification_approval=False, probabilities_compared=False, process_liveness='NOT_CHECKED',
        limitations=[
            'ERROR journals require investigation; all their selected saved conditions must be rerun after resolving the error.',
            'A saved condition absent from its journal cannot be omitted from the fresh-directory restart plan.',
            'Saved-row coverage is not proof of execution or an independently approved rerun.',
            'Legacy partial outputs have no authenticated input/environment/source lineage; do not silently append or adopt them.',
            'Each completed journal covers only its requested model and epsilons, never Gaussian/Mean or other conditions.',
            'A persisted RUNNING status does not establish that a process is still alive.',
            'Multiple directories remain separate invocations; matching labels do not establish identical runtime provenance.',
        ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dirs', type=Path, nargs='+')
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--models', choices=tuple(MODELS), nargs='+', default=list(MODELS))
    parser.add_argument('--epsilons', type=float, nargs='+', default=list(DEFAULT_EPSILONS))
    parser.add_argument('--allow-partial', action='store_true', help='Permit partial-coverage exit 0 for resume planning; result still says PARTIAL')
    args = parser.parse_args()
    result = audit(args.run_dirs, args.repo_root, args.models, args.epsilons)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    if result['execution_errors']:
        return 3  # --allow-partial cannot override a recorded execution error.
    return 2 if (result['missing_conditions'] or result['rerun_conditions']) and not args.allow_partial else 0


if __name__ == '__main__':
    raise SystemExit(main())
