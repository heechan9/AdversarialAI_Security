import ast
import json
from pathlib import Path
import pytest
from verification.recovery_stage import backup


def test_backup_preserves_bytes_and_rejects_symlink(tmp_path):
    source=tmp_path/'source';target=tmp_path/'backup';source.mkdir()
    (source/'run.json').write_text('{"status":"RUNNING"}')
    (source/'best.keras').write_bytes(b'private weights')
    backup(source,target)
    assert (target/'run.json').read_bytes()==(source/'run.json').read_bytes()
    assert (target/'best.keras').read_bytes()==(source/'best.keras').read_bytes()
    (source/'unsafe.csv').symlink_to(source/'run.json')
    with pytest.raises(ValueError):backup(source,target)


def test_recovery_notebook_has_no_saved_outputs_and_valid_python():
    root=Path(__file__).resolve().parents[1]
    notebook=json.loads((root/'notebooks/AdversarialAI_Recovery_GPU.ipynb').read_text())
    for cell in notebook['cells']:
        if cell['cell_type']=='code':
            assert cell['outputs']==[] and cell['execution_count'] is None
            ast.parse(''.join(cell['source']))
    source=''.join(''.join(c['source']) for c in notebook['cells'])
    assert '--resume-from' in source
    assert 'audit_all(BIM,PGD,JSMA,TRAIN,EVAL,REPO)' in source


def test_recovery_notebook_inherits_13_condition_parent_at_pinned_source():
    root=Path(__file__).resolve().parents[1]
    notebook=json.loads((root/'notebooks/AdversarialAI_Recovery_GPU.ipynb').read_text())
    source=''.join(''.join(c['source']) for c in notebook['cells'])
    # The earlier 11-condition parent must not be reused.
    assert "['checked_conditions']==11" not in source
    assert "locate('full-gpu-20261004T120332-pgd')" not in source
    assert "recovery-20261005T165652" in source and "'pgd'/'outputs'" in source
    assert "parent_audit['checked_conditions']==13" in source
    assert "parent_report['source_commit']==COMMIT" in source
    # Remaining PGD conditions are exactly MobileNet Mean eps .01/.03/.05.
    assert "('mobilenet','mean',e) for e in (.01,.03,.05)" in source
    # Source is pinned explicitly; no dynamic HEAD/branch checkout and no check removal.
    assert "Explicit reviewed SHA required" in source
    assert "checkout','--detach',COMMIT" in source
    assert "origin/HEAD" not in source and "'checkout','main'" not in source
    assert source.count("--resume-from")==1
