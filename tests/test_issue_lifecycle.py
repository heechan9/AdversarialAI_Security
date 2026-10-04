import copy
import hashlib
import json
from pathlib import Path
import shutil
import pytest
from verification.issue_lifecycle import LOG, build, transition, validate_issue

ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def case(tmp_path):
    data=json.loads((ROOT/LOG).read_text())
    issue=data['issues'][0]
    paths={LOG,'configs/test_manifest.json','configs/stage_b_verification_contract.json'}
    paths.update(e['path'] for h in issue['history'] for e in h['evidence'])
    for p in paths:
        dest=tmp_path/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,dest)
    return tmp_path,issue

def event(issue, action):
    return dict(action=action,at='2026-10-02T00:00:00+00:00',actor_role='reviewer',source_commit='a'*40,note='Synthetic test only',evidence=copy.deepcopy(issue['history'][-1]['evidence']))

def report(root,issue,action='retest_pass',mutate=lambda x: None):
    r=dict(kind='cross_environment_retest',issue_id=issue['id'],source_commit='a'*40,scope=copy.deepcopy(issue['scope']),model_sha256=copy.deepcopy(issue['model_sha256']),manifest_sha256=issue['manifest_sha256'],operator_role='external_operator',independent_operator=True,comparison=dict(label_match_fraction=1.0,metric_abs_tolerance=1e-6,linf_tolerance=1e-6),completed=True,result='PASS' if action=='retest_pass' else 'FAIL',difference_count=0 if action=='retest_pass' else 1)
    mutate(r)
    p='results/verification/synthetic-test.json';raw=json.dumps(r).encode();(root/p).write_bytes(raw)
    e=event(issue,action);e['evidence']=[dict(path=p,sha256=hashlib.sha256(raw).hexdigest())];return e

def test_current_open(case):
    root,issue=case
    assert build(root)[0]['state']=='open'

def test_close_reopen_preserves_history(case):
    root,issue=case;original=copy.deepcopy(issue)
    waiting=transition(root,issue,event(issue,'action_recorded'))
    closed=transition(root,waiting,report(root,waiting))
    reopened=transition(root,closed,event(closed,'reopen'))
    assert closed['state']=='closed' and reopened['state']=='open'
    assert issue==original and reopened['history'][:2]==original['history']

def test_failed_retest_reopens(case):
    root,issue=case;waiting=transition(root,issue,event(issue,'action_recorded'))
    assert transition(root,waiting,report(root,waiting,'retest_fail'))['state']=='open'

def test_local_pass_cannot_close(case):
    root,issue=case;waiting=transition(root,issue,event(issue,'action_recorded'))
    with pytest.raises(ValueError):transition(root,waiting,event(waiting,'retest_pass'))

@pytest.mark.parametrize('mutate',[
 lambda r:r.update(independent_operator=False),lambda r:r.update(operator_role='research_operator'),
 lambda r:r.update(completed=False),lambda r:r.update(difference_count=1),
 lambda r:r.update(source_commit='b'*40),lambda r:r.update(issue_id='other'),
 lambda r:r['scope'].update(samples=780),lambda r:r['comparison'].update(metric_abs_tolerance=0.01),
 lambda r:r['model_sha256'].update(cnn='0'*64)])
def test_invalid_retest_rejected(case,mutate):
    root,issue=case;waiting=transition(root,issue,event(issue,'action_recorded'))
    with pytest.raises(ValueError):transition(root,waiting,report(root,waiting,mutate=mutate))

def test_cannot_skip_action(case):
    root,issue=case
    with pytest.raises(ValueError):transition(root,issue,report(root,issue))

@pytest.mark.parametrize('mutate',[
 lambda i:i.update(state='closed'),lambda i:i['history'].reverse(),
 lambda i:i['history'][1].update(seq=0),lambda i:i['history'][1].update(at='2026-10-01'),
 lambda i:i['history'][1].update(evidence=[]),lambda i:i['history'][1].update(action='retest_pass')])
def test_corrupt_history_rejected(case,mutate):
    root,issue=case;mutate(issue)
    with pytest.raises(ValueError):validate_issue(root,issue)
