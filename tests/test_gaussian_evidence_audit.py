import importlib.util
import io
import json
from pathlib import Path
import shutil
import zipfile
import pytest

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('independent_gaussian',REPO/'scripts/audit_gaussian_defense.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_archived_run():
    assert module.audit(REPO,REPO/'results/defenses/experimental/gaussian_run_01')['status']=='PASSED'


@pytest.fixture
def evidence(tmp_path):
    return Path(shutil.copytree(REPO/'results/defenses/experimental/gaussian_run_01',tmp_path/'evidence'))


def repack(root):
    """Re-sign hashes too: semantic checks must still reject mutations."""
    checks=json.loads((root/'SHA256.json').read_text())
    for name in checks: checks[name]=module.digest((root/name).read_bytes())
    (root/'SHA256.json').write_text(json.dumps(checks))
    c=json.loads((root/'COMPLETE.json').read_text());c['summary_sha256']=checks['summary.json'];c['checksums_sha256']=module.digest((root/'SHA256.json').read_bytes())
    (root/'COMPLETE.json').write_text(json.dumps(c))
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        for name in list(checks)+['SHA256.json','COMPLETE.json']:z.writestr('run/'+name,(root/name).read_bytes())
    (root/'original_bundle.zip').write_bytes(b.getvalue())
    p=json.loads((root/'PROVENANCE.json').read_text());p['original_bundle_sha256']=module.digest(b.getvalue())
    (root/'PROVENANCE.json').write_text(json.dumps(p))


@pytest.mark.parametrize('change',['denominator','class','extra','zero','nonfinite','schema','promoted'])
def test_semantic_mutations_even_with_updated_hashes(evidence,change):
    if change in ['denominator','class','extra']:
        p=evidence/'summary.json';s=json.loads(p.read_text())
        if change=='denominator':s[0]['overall']['asr_adaptive_defended']['denominator']+=1
        if change=='class':next(iter(s[0]['classes'].values()))['samples']+=1
        if change=='extra':s.append(s[0])
        p.write_text(json.dumps(s))
    elif change=='promoted':
        p=evidence/'COMPLETE.json';s=json.loads(p.read_text());s['promoted']=True;p.write_text(json.dumps(s))
    else:
        p=evidence/'cnn_eps_0_samples.csv';s=p.read_text()
        if change=='schema':s=s.replace('adaptive_linf','bad_column')
        else:
            lines=s.splitlines();row=lines[1].split(',');row[-1]='0.0000001' if change=='zero' else 'nan';lines[1]=','.join(row);s='\n'.join(lines)+'\n'
        p.write_text(s)
    repack(evidence)
    with pytest.raises(ValueError):module.audit(REPO,evidence)


def test_archive_bytes_cannot_silently_change(evidence):
    with (evidence/'summary.json').open('ab') as f:f.write(b' ')
    with pytest.raises(ValueError,match='archive member mismatch'):module.audit(REPO,evidence)


def test_duplicate_json_and_nonfinite_fail():
    for raw in ['{"a":1,"a":2}','{"a":NaN}']:
        with pytest.raises(ValueError):module.document(raw)
