"""Codex reproductions of Stage A parser and output-integrity gaps."""
import csv
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from verification.stage_a_clean_recompute import main, run_stage_a, recompute_confusion_matrix, VerificationError


@pytest.fixture
def evidence(tmp_path):
    root = tmp_path / 'repo'
    shutil.copytree('configs', root / 'configs')
    shutil.copytree('results/clean', root / 'results/clean')
    return root


@pytest.mark.parametrize('kind', ['json_duplicate', 'csv_duplicate', 'extra_column', 'report_extra_column', 'bad_encoding', 'duplicate_roster', 'unsafe_roster', 'duplicate_class'])
def test_ambiguous_or_invalid_inputs_fail(evidence, kind):
    clean = evidence / 'results/clean'
    if kind == 'json_duplicate':
        p = clean / 'cnn_baseline_report.json'
        p.write_text('{"accuracy": -123,' + p.read_text().lstrip()[1:])
    elif kind in ('csv_duplicate', 'extra_column', 'report_extra_column'):
        p = clean / ('cnn_baseline_report.csv' if kind == 'report_extra_column' else 'cnn_baseline_eval.csv')
        with p.open(newline='') as f:
            rows = list(csv.reader(f))
        rows[0].insert(0, 'predicted_label' if kind == 'csv_duplicate' else 'unexpected')
        for row in rows[1:]:
            row.insert(0, 'FAKE')
        with p.open('w', newline='') as f:
            csv.writer(f).writerows(rows)
    elif kind == 'bad_encoding':
        (clean / 'cnn_baseline_report.json').write_bytes(b'\xff')
    elif kind in ('duplicate_roster', 'unsafe_roster'):
        p = evidence / 'configs/experiment.yaml'
        if kind == 'duplicate_roster':
            p.write_text(p.read_text() + '\nmodels:\n  other:\n')
        else:
            p.write_text(p.read_text().replace('  cnn_baseline:', '  ../cnn_baseline:'))
    else:
        p = evidence / 'configs/classes.json'
        obj = json.loads(p.read_text()); obj['1'] = obj['0']; p.write_text(json.dumps(obj))
    assert run_stage_a(evidence)['status'] == 'FAIL'


@pytest.mark.parametrize('target', ['configs/classes.json', 'results/clean/cnn_baseline_summary.json', 'verification/new.json', 'results/verification/existing.json'])
def test_report_cannot_overwrite_or_write_into_inputs(evidence, target):
    p = evidence / target
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text('keep')
    before = p.read_bytes()
    assert main(['--repo-root', str(evidence), '--output', str(p)]) == 1
    assert p.read_bytes() == before


def test_default_run_is_read_only(evidence):
    before = {p.relative_to(evidence): p.read_bytes() for p in evidence.rglob('*') if p.is_file()}
    assert main(['--repo-root', str(evidence)]) == 0
    assert before == {p.relative_to(evidence): p.read_bytes() for p in evidence.rglob('*') if p.is_file()}


def test_output_symlink_rejected(evidence, tmp_path):
    target = tmp_path / 'out'; target.mkdir()
    link = evidence / 'results/verification'
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('symlinks unavailable')
    assert main(['--repo-root', str(evidence), '--output', str(link / 'new.json')]) == 1
    assert not list(target.iterdir())


def test_worktree_source_commit_is_resolved():
    root = Path('.')
    expected = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    assert run_stage_a(root)['verified_commit'] == expected


def test_metric_length_mismatch_fails():
    with pytest.raises(VerificationError, match='lengths'):
        recompute_confusion_matrix(['a', 'b'], ['a'], ['a', 'b'])
