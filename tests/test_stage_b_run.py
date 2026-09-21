import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from verification import stage_b_run as runner
from verification.maris_source_check import check

ROOT = Path(__file__).resolve().parents[1]


def test_canonical_maris_snapshot():
    assert check(ROOT)['defense_conditions'] == 16


def test_web_tamper_even_with_updated_export_hash(tmp_path):
    import hashlib
    shutil.copytree(ROOT/'web/maris/public/evidence', tmp_path/'web/maris/public/evidence')
    shutil.copytree(ROOT/'results', tmp_path/'results')
    shutil.copytree(ROOT/'configs', tmp_path/'configs')
    p=tmp_path/'web/maris/public/evidence/data.json'
    d=json.loads(p.read_text()); d['results'][0]['robustCorrect']-=1
    p.write_text(json.dumps(d))
    provenance=p.with_name('provenance.json'); v=json.loads(provenance.read_text())
    v['export_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();provenance.write_text(json.dumps(v))
    with pytest.raises(ValueError, match='numeric mismatch'):
        check(tmp_path)


@pytest.mark.parametrize('method',['gaussian','mean'])
def test_comparator_real_saved_rows_and_mutation(tmp_path,method):
    source=ROOT/f'results/defenses/experimental/{method}_run_01'
    output=tmp_path/method;shutil.copytree(source,output)
    contract=json.loads((ROOT/'configs/stage_b_verification_contract.json').read_text())
    assert runner.compare_outputs(ROOT,output,method,contract)['rows_compared']==6248
    file=output/'cnn_eps_0_samples.csv'
    rows=runner.read_rows(file);rows[0]['adaptive_defended_pred']=str((int(rows[0]['adaptive_defended_pred'])+1)%10)
    import csv
    with file.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with pytest.raises(ValueError,match='label/path mismatch'):
        runner.compare_outputs(ROOT,output,method,contract)


@pytest.mark.parametrize('fail',[False,True])
def test_orchestration_report_and_no_overwrite(tmp_path,monkeypatch,fail):
    monkeypatch.setattr(runner.platform,'platform',lambda:'test platform')
    root=tmp_path/'repo';root.mkdir()
    contract=json.loads((ROOT/'configs/stage_b_verification_contract.json').read_text())
    contract['outputs']['run_id']='test-01'
    path=tmp_path/'contract.json';path.write_text(json.dumps(contract))
    monkeypatch.setattr(runner,'check_stage_b_readiness',lambda *a:{'ready':True,'blockers':[]})
    def fake_run(cmd,**kw):
        if 'freeze' in cmd:return SimpleNamespace(stdout='mock environment\n')
        if fail:raise RuntimeError('simulated inference failure')
        Path(cmd[-1]).mkdir()
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runner.subprocess,'run',fake_run)
    monkeypatch.setattr(runner,'compare_outputs',lambda *a:{'status':'PASS'})
    if fail:
        with pytest.raises(RuntimeError):runner.run(root,path)
    else:
        assert runner.run(root,path)['status']=='PASS'
    report=json.loads((tmp_path/'stage-b-test-01/rerun-report.json').read_text())
    assert report['status']==('FAIL' if fail else 'PASS')
    assert len(report['commands'])==(1 if fail else 2)
    with pytest.raises(FileExistsError):runner.run(root,path)


def test_not_ready_never_starts_process(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'check_stage_b_readiness',lambda *a:{'ready':False,'blockers':['assets missing']})
    monkeypatch.setattr(runner.subprocess,'run',lambda *a,**k:pytest.fail('must not execute'))
    with pytest.raises(ValueError,match='assets missing'):
        runner.run(tmp_path,tmp_path/'absent.json')
