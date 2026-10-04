"""Mutation tests: a local success cannot hide external failure or stale evidence."""
import hashlib
import json
from pathlib import Path
import shutil
import pytest
from verification.status_registry import REGISTRY, SNAPSHOT, build, sync

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def repo(tmp_path):
    for name in [REGISTRY,SNAPSHOT,'README.md','results/verification/discrepancy_log.json','configs/test_manifest.json','configs/stage_b_verification_contract.json']:
        dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest)
    registry=json.loads((tmp_path/REGISTRY).read_text())
    for record in registry['records']:
        for name in [record['report_path'],*[e['path'] for e in record['evidence']]]:
            dest=tmp_path/name;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,dest)
    return tmp_path


def edit_registry(root, fn):
    p=root/REGISTRY;data=json.loads(p.read_text());fn(data)
    p.write_text(json.dumps(data))


def mutate_evidence(root, fn):
    reg=json.loads((root/REGISTRY).read_text());e=reg['records'][0]['evidence'][0]
    p=root/e['path'];d=json.loads(p.read_text());fn(d);p.write_text(json.dumps(d))
    e['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    (root/REGISTRY).write_text(json.dumps(reg))


def test_current_status_is_separate_and_read_only(repo):
    before={p:p.read_bytes() for p in repo.rglob('*') if p.is_file()}
    s=sync(repo)
    assert [c['status'] for c in s['cards']]==['LOCAL_PASS','FAIL']
    assert s['cause_status']=='UNRESOLVED'
    assert before=={p:p.read_bytes() for p in before}


@pytest.mark.parametrize('mutation',[
    lambda r:r['records'][0].update(operator_role='external_operator'),
    lambda r:r['records'][1].update(status='PASS'),
    lambda r:r['records'].pop(),
    lambda r:r['records'].append(r['records'][0]),
    lambda r:r['records'][1]['evidence'].pop(),
    lambda r:r['records'][0].update(source_commit='0'*40),
    lambda r:r['records'][0]['evidence'][0].update(path='../secret.json'),
])
def test_registry_cannot_promote_or_lose_scope(repo,mutation):
    edit_registry(repo,mutation)
    with pytest.raises(ValueError):build(repo)


@pytest.mark.parametrize('mutation',[
    lambda d:d.update(independent_operator=True),
    lambda d:d.update(cause_confirmed=True),
    lambda d:d.update(probabilities_compared=True),
    lambda d:d.update(metric_abs_tolerance=.01),
    lambda d:d['comparisons_recomputed'].pop(),
    lambda d:d['comparisons_recomputed'][0].update(differences=[{'changed':True}]),
    lambda d:d.update(rows_per_csv=780),
    lambda d:d.update(zip_crc_ok=False),
])
def test_changed_evidence_still_needs_valid_semantics(repo,mutation):
    mutate_evidence(repo,mutation)
    with pytest.raises(ValueError):build(repo)


def test_hash_changes_fail_before_publication(repo):
    reg=json.loads((repo/REGISTRY).read_text())
    p=repo/reg['records'][0]['evidence'][0]['path'];p.write_text(p.read_text()+' ')
    with pytest.raises(ValueError,match='evidence changed'):sync(repo,write=True)


@pytest.mark.parametrize('file',[SNAPSHOT,'README.md'])
def test_stale_display_fails_and_regenerates(repo,file):
    p=repo/file;p.write_text(p.read_text().replace('LOCAL_PASS','PASS'))
    with pytest.raises(ValueError,match='stale'):sync(repo)
    sync(repo,write=True)
    sync(repo)


def test_missing_evidence_is_not_unknown_success(repo):
    reg=json.loads((repo/REGISTRY).read_text());(repo/reg['records'][0]['evidence'][0]['path']).unlink()
    with pytest.raises(FileNotFoundError):build(repo)
