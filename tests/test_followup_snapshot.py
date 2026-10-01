import hashlib
import json
from pathlib import Path
import pytest
from verification.followup_snapshot import capture

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/extensions/checkpoints/20261001/bim'


def test_real_partial_evidence_is_preserved(tmp_path):
    out = tmp_path / 'snapshot'
    result = capture(SOURCE, out, ROOT)
    assert result['result'] == 'PARTIAL_OUTPUTS_ONLY'
    assert (out/'run.json').read_bytes() == (SOURCE/'run.json').read_bytes()
    index = json.loads((out/'snapshot.json').read_text())
    assert index['live_status'] is False
    for name, digest in index['files'].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest() == digest
    assert '| defended_clean | 56.98 | N/A | N/A |' in (out/'SUMMARY.md').read_text()
    with pytest.raises(FileExistsError):
        capture(SOURCE, out, ROOT)


def test_corruption_leaves_no_published_snapshot(tmp_path):
    import shutil
    source = tmp_path/'source'
    shutil.copytree(SOURCE, source)
    csv = next(source.glob('*.csv'))
    csv.write_bytes(csv.read_bytes() + b'corrupted\n')
    out = tmp_path/'snapshot'
    with pytest.raises(ValueError, match='hash mismatch'):
        capture(source, out, ROOT)
    assert not out.exists()
    assert not list(tmp_path.glob('.snapshot-*'))


def test_continuation_preserves_lineage_and_rejects_settings(tmp_path,monkeypatch):
    from copy import deepcopy
    from adversarial_ai.evaluation.continuation import carry_forward
    from verification.iterative_result_audit import audit
    import subprocess
    parent=json.loads((SOURCE/'run.json').read_text())
    report=deepcopy(parent);report['source_commit']='b'*40
    out=tmp_path/'continue';out.mkdir()
    monkeypatch.setattr(subprocess,'check_output',lambda *a,**k:'src/adversarial_ai/evaluation/iterative_evaluation.py\n')
    completed=carry_forward(SOURCE,out,report,ROOT)
    assert len(completed)==3
    assert report['continuation']['parent_source_commit']==parent['source_commit']
    (out/'run.json').write_text(json.dumps(report))
    assert audit(out,ROOT)['result']=='PARTIAL_OUTPUTS_ONLY'
    capture(out,tmp_path/'snapshot',ROOT)
    bad=deepcopy(report);bad['settings']['seed']+=1
    with pytest.raises(ValueError,match='setting mismatch'):
        carry_forward(SOURCE,out,bad,ROOT)
    monkeypatch.setattr(subprocess,'check_output',lambda *a,**k:'src/adversarial_ai/attacks/iterative.py\n')
    with pytest.raises(ValueError,match='source differs'):
        carry_forward(SOURCE,out,report,ROOT)
    (out/'parent-run.json').write_text('{}')
    with pytest.raises(ValueError,match='parent report hash'):
        audit(out,ROOT)
