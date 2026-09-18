"""Synthetic readiness/capture tests; these do not execute or approve FGSM."""
import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from adversarial_ai.audit.official_readiness import check_official_fgsm_readiness
from scripts.capture_official_fgsm_context import capture_context


@pytest.fixture
def ready_fixture(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    shutil.copytree('configs', root / 'configs')
    (root / 'results/clean').mkdir(parents=True)
    (root / 'data/test').mkdir(parents=True)
    hashes = {}
    for name in ('cnn_baseline_metadata.json', 'mobilenet_metadata.json'):
        meta = json.loads((Path('results/clean') / name).read_text())
        model = root / meta['model_path']; model.parent.mkdir(exist_ok=True)
        model.write_bytes(b'test fixture; not a model')
        meta['model_sha256'] = hashlib.sha256(model.read_bytes()).hexdigest()
        hashes[meta['model_path']] = meta['model_sha256']
        (root / 'results/clean' / name).write_text(json.dumps(meta))
    monkeypatch.setattr('adversarial_ai.audit.official_readiness.audit_manifest', lambda *a, **k: {'manifest_models': hashes})
    monkeypatch.setattr('adversarial_ai.audit.official_readiness.get_git_commit_sha', lambda root: 'a' * 40)
    monkeypatch.setattr('adversarial_ai.audit.official_readiness.subprocess.run', lambda *a, **k: SimpleNamespace(stdout=''))
    monkeypatch.setattr('scripts.capture_official_fgsm_context.version', lambda _: 'test-runtime')
    contract = json.loads((root / 'configs/fgsm_official_contract.json').read_text())
    contract.update(status='approved', source_git_commit='a' * 40,
                    approval={'approved_by': 'synthetic fixture only', 'approved_at': '2026-01-01T00:00:00Z'})
    contract['experiment']['epsilons'] = [0, 0.01, 0.03, 0.05]
    contract['outputs']['run_id'] = 'test-run'
    path = tmp_path / 'external-run-contract.json'
    path.write_text(json.dumps(contract))
    return root, path, contract


def test_complete_fixture_is_ready_and_preparation_cannot_overwrite(ready_fixture):
    root, path, _ = ready_fixture
    assert check_official_fgsm_readiness(root, path) == {'ready': True, 'blockers': []}
    out = capture_context(root, path)
    assert out == root / 'results/attacks/official_candidate/test-run'
    assert (out / 'run_contract.json').read_bytes() == path.read_bytes()
    context = json.loads((out / 'official_execution_context.json').read_text())
    assert context['contract_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    with pytest.raises(ValueError, match='already exists'):
        capture_context(root, path)
    assert before == {p.name: p.read_bytes() for p in out.iterdir()}


@pytest.mark.parametrize('mutation', ['pending', 'schema_bool', 'steps_bool', 'range_bool', 'epsilon_bool', 'epsilon_unsupported', 'unsafe_run', 'windows_device', 'wrong_root', 'future_date', 'wrong_sha', 'metadata_array', 'duplicate_key', 'dirty_checkout', 'missing_binary', 'tampered_binary'])
def test_invalid_contract_or_inputs_block_preparation(ready_fixture, mutation, monkeypatch):
    root, path, c = ready_fixture
    if mutation == 'pending': c['status'] = 'pending_team_confirmation'
    if mutation == 'schema_bool': c['schema_version'] = True
    if mutation == 'steps_bool': c['experiment']['steps'] = True
    if mutation == 'range_bool': c['experiment']['input_range'] = [False, True]
    if mutation == 'epsilon_bool': c['experiment']['epsilons'][0] = False
    if mutation == 'epsilon_unsupported': c['experiment']['epsilons'] = [0, 0.02]
    if mutation == 'unsafe_run': c['outputs']['run_id'] = '../provisional'
    if mutation == 'windows_device': c['outputs']['run_id'] = 'con'
    if mutation == 'wrong_root': c['outputs']['root'] = 'results/attacks/official'
    if mutation == 'future_date': c['approval']['approved_at'] = '2999-01-01T00:00:00Z'
    if mutation == 'wrong_sha': c['source_git_commit'] = 'b' * 40
    if mutation == 'metadata_array': (root / 'results/clean/cnn_baseline_metadata.json').write_text('[]')
    if mutation == 'missing_binary': (root / 'models/cnn_baseline.h5').unlink()
    if mutation == 'tampered_binary': (root / 'models/cnn_baseline.h5').write_bytes(b'changed')
    if mutation == 'dirty_checkout':
        monkeypatch.setattr('adversarial_ai.audit.official_readiness.subprocess.run', lambda *a, **k: SimpleNamespace(stdout='src/changed.py\n'))
    path.write_text(json.dumps(c))
    if mutation == 'duplicate_key': path.write_text('{"status":"pending",' + path.read_text()[1:])
    assert not check_official_fgsm_readiness(root, path)['ready']
    with pytest.raises(ValueError, match='blocked'):
        capture_context(root, path)
    assert not (root / 'results/attacks/official_candidate').exists()


def test_approved_contract_cannot_refer_to_its_own_commit(ready_fixture):
    root, path, _ = ready_fixture
    local = root / 'configs/fgsm_official_contract.json'; local.write_bytes(path.read_bytes())
    r = check_official_fgsm_readiness(root, local)
    assert not r['ready']
    assert any('self-referential' in b for b in r['blockers'])


def test_candidate_parent_symlink_fails(ready_fixture, tmp_path):
    root, path, _ = ready_fixture
    target = tmp_path / 'other'; target.mkdir()
    (root / 'results/attacks').mkdir()
    link = root / 'results/attacks/official_candidate'
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('symlinks unavailable')
    assert not check_official_fgsm_readiness(root, path)['ready']
    with pytest.raises(ValueError): capture_context(root, path)
    assert list(target.iterdir()) == []
