"""A rehashed result must still obey the declared query budget."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'verification'))
from surfree_saved_audit import audit


def test_rehashed_query_budget_violation_is_rejected(tmp_path):
    source=ROOT/'results/extensions/surfree/cnn_original_smoke50_20261003'
    shutil.copytree(source,tmp_path/'run')
    folder=tmp_path/'run'
    assert audit(folder)==10
    rows=[json.loads(x) for x in (folder/'samples.jsonl').read_text().splitlines()]
    rows[0]['queries']=51
    raw=''.join(json.dumps(r)+'\n' for r in rows).encode()
    (folder/'samples.jsonl').write_bytes(raw)
    report=json.loads((folder/'run.json').read_text())
    report['samples_sha256']=hashlib.sha256(raw).hexdigest()
    (folder/'run.json').write_text(json.dumps(report))
    with pytest.raises(AssertionError):audit(folder)
