"""Synthetic journal mutations over public saved rows; no model execution."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from verification.fgsm_run_audit import audit, audit_condition, read_json, sha

ROOT = Path(__file__).resolve().parents[1]
EPSILONS = [0., .01, .03, .05]


def journal_fixture(tmp_path, saved, recorded, status='ERROR', model='mobilenet'):
    out = tmp_path/model
    out.mkdir()
    manifest = read_json(ROOT/'configs/test_manifest.json')
    classes = read_json(ROOT/'configs/classes.json')
    for epsilon in saved:
        for suffix in ('samples.csv','report.json','confusion_matrix.csv','confusion_matrix.png'):
            name = f'fgsm_{model}_eps_{epsilon:g}_{suffix}'
            shutil.copyfile(ROOT/'results/attacks/provisional'/name, out/name)
    model_path = 'models/cnn_baseline.h5' if model == 'cnn' else 'models/mobilenet_finetuned.h5'
    journal = dict(schema_version=1, kind='fgsm_evaluation_progress', model=model,
                   independent_verification_approval=False, status=status, epsilons=EPSILONS,
                   conditions=[], run_id='synthetic-journal-fixture',
                   error='RuntimeError: synthetic integrity-check failure',
                   model_sha256=next(v['sha256'] for v in manifest['models'] if v['path']==model_path),
                   manifest_sha256=sha(ROOT/'configs/test_manifest.json'),
                   classes_sha256=sha(ROOT/'configs/classes.json'))
    for epsilon in recorded:
        metrics, _ = audit_condition(out/f'fgsm_{model}_eps_{epsilon:g}_samples.csv', epsilon, manifest, classes)
        journal['conditions'].append(dict(epsilon=epsilon, samples=781, summary=metrics,
            artifact_sha256={p.name:sha(p) for p in out.glob(f'fgsm_{model}_eps_{epsilon:g}_*')}))
    (out/f'fgsm_{model}_execution.json').write_text(json.dumps(journal), encoding='utf-8')
    return out


def restart_epsilons(result):
    return result['resume_plan'][0]['epsilons']


def cli(out, *extra):
    return subprocess.run([sys.executable, str(ROOT/'verification/fgsm_run_audit.py'),
                           str(out),'--models','mobilenet',*extra], capture_output=True, text=True)


def test_error_unrecorded_csv_is_not_omitted_from_restart(tmp_path):
    out = journal_fixture(tmp_path, EPSILONS[:3], EPSILONS[:2])
    result = audit([out], ROOT, ['mobilenet'])
    assert result['checked_conditions'] == 3  # Physical saved-row coverage is retained.
    assert result['saved_sample_coverage'] == 'PARTIAL_SAVED_SAMPLE_COVERAGE'
    assert result['result'] == 'RECORDED_EXECUTION_ERROR'
    assert restart_epsilons(result) == EPSILONS
    assert result['invocations'][0]['unrecorded_saved_epsilons'] == [.03]
    assert result['invocations'][0]['provenance'] == 'RECORDED_ERROR_ARTIFACTS_ONLY'
    assert result['resume_requires_error_resolution'] is True


@pytest.mark.parametrize('extra', [[], ['--allow-partial']])
def test_error_after_all_records_is_nonzero_even_with_allow_partial(tmp_path, extra):
    out = journal_fixture(tmp_path, EPSILONS, EPSILONS)
    completed = cli(out, *extra)
    assert completed.returncode == 3
    result = json.loads(completed.stdout)
    assert result['result'] == 'RECORDED_EXECUTION_ERROR'
    assert result['saved_sample_coverage'] == 'FULL_REQUESTED_SAVED_SAMPLE_COVERAGE'
    assert result['missing_conditions'] == []
    assert restart_epsilons(result) == EPSILONS
    assert len(result['rerun_conditions']) == 4
    assert not result['invocations'][0]['completion_record_consistent']


@pytest.mark.parametrize('status', ['PREPARING','RUNNING','INTERRUPTED'])
def test_unjournaled_condition_requires_restart_without_error_status(tmp_path, status):
    out = journal_fixture(tmp_path, EPSILONS[:3], EPSILONS[:2], status)
    result = audit([out], ROOT, ['mobilenet'])
    assert result['result'] == 'SAVED_CONDITIONS_REQUIRE_RERUN'
    assert restart_epsilons(result) == [.03, .05]
    assert result['execution_errors'] == []
    assert result['rerun_conditions'] == [dict(model='mobilenet',epsilon=.03,
                                              reason='SAVED_CONDITION_NOT_IN_JOURNAL')]
    assert result['invocations'][0]['provenance'] == 'JOURNAL_WITH_UNRECORDED_SAVED_CONDITIONS'
    assert cli(out).returncode == 2
    assert cli(out, '--allow-partial').returncode == 0


def test_full_saved_coverage_with_unrecorded_condition_still_requires_restart(tmp_path):
    out = journal_fixture(tmp_path, EPSILONS, EPSILONS[:3], 'RUNNING')
    result = audit([out], ROOT, ['mobilenet'])
    assert result['saved_sample_coverage'] == 'FULL_REQUESTED_SAVED_SAMPLE_COVERAGE'
    assert result['result'] == 'SAVED_CONDITIONS_REQUIRE_RERUN'
    assert result['missing_conditions'] == []
    assert restart_epsilons(result) == [.05]
    assert cli(out).returncode == 2


def test_interrupted_recorded_conditions_remain_reusable_for_planning(tmp_path):
    out = journal_fixture(tmp_path, EPSILONS[:2], EPSILONS[:2], 'INTERRUPTED')
    result = audit([out], ROOT, ['mobilenet'])
    assert result['result'] == 'PARTIAL_SAVED_SAMPLE_COVERAGE'
    assert restart_epsilons(result) == [.03, .05]
    assert result['rerun_conditions'] == []
    assert result['invocations'][0]['validated_recorded_epsilons'] == EPSILONS[:2]


def test_error_without_saved_conditions_cannot_be_allowed_partial(tmp_path):
    out = journal_fixture(tmp_path, [], [])
    result = audit([out], ROOT, ['mobilenet'])
    assert result['result'] == 'RECORDED_EXECUTION_ERROR'
    assert restart_epsilons(result) == EPSILONS
    assert cli(out, '--allow-partial').returncode == 3


def test_error_plan_is_selected_scope_only_and_does_not_mutate_files(tmp_path):
    out = journal_fixture(tmp_path, EPSILONS, EPSILONS)
    before = {p.name:p.read_bytes() for p in out.iterdir()}
    result = audit([out], ROOT, ['mobilenet'], [.05, .01])
    assert restart_epsilons(result) == [.05, .01]
    assert {p.name:p.read_bytes() for p in out.iterdir()} == before


def test_error_in_one_model_does_not_require_rerun_of_other_model(tmp_path):
    bad = journal_fixture(tmp_path, EPSILONS, EPSILONS)
    other = journal_fixture(tmp_path, EPSILONS, EPSILONS, 'INTERRUPTED', 'cnn')
    result = audit([bad, other], ROOT)
    assert result['result'] == 'RECORDED_EXECUTION_ERROR'
    assert result['resume_plan'] == [dict(model='mobilenet', epsilons=EPSILONS,
        output_requirement='NEW_DIRECTORY_OUTSIDE_ALL_PRIOR_OUTPUTS')]


def test_legacy_coverage_contract_is_unchanged(tmp_path):
    out = journal_fixture(tmp_path, EPSILONS, [])
    (out/'fgsm_mobilenet_execution.json').unlink()
    result = audit([out], ROOT, ['mobilenet'])
    assert result['result'] == 'FULL_REQUESTED_SAVED_SAMPLE_COVERAGE'
    assert result['resume_plan'] == [] and result['rerun_conditions'] == []
    assert result['invocations'][0]['provenance'] == 'LEGACY_EXECUTION_PROVENANCE_UNVERIFIED'
    assert cli(out).returncode == 0
