import json
from pathlib import Path
import pytest
from verification.jsma_saved_audit import audit

SOURCE=Path(__file__).resolve().parents[1]/'results/extensions/checkpoints/20261001/jsma/run.json'

def saved(tmp_path):
    data=json.loads(SOURCE.read_text())
    (tmp_path/'run.json').write_text(json.dumps(data))
    return data

def test_preserved_partial_is_not_full(tmp_path):
    saved(tmp_path)
    assert audit(tmp_path)['result']=='PARTIAL_SAVED_EVIDENCE_ONLY'

@pytest.mark.parametrize('mutation',['target','budget','coverage'])
def test_tampered_evidence_rejected(tmp_path,mutation):
    data=saved(tmp_path)
    if mutation=='target':data['rows'][0]['target']=(data['rows'][0]['target']+1)%10
    if mutation=='budget':data['rows'][0]['changed_features']=data['rows'][0]['budget_features']+1
    if mutation=='coverage':data['status']='FULL_COVERAGE_NOT_ROBUSTNESS_PROOF'
    (tmp_path/'run.json').write_text(json.dumps(data))
    with pytest.raises(AssertionError):audit(tmp_path)
