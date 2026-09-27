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
        if 'verification.stage_b_preflight' in cmd:return SimpleNamespace(returncode=0)
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
    assert len(report['commands'])==(1 if fail else 3)
    with pytest.raises(FileExistsError):runner.run(root,path)


def test_not_ready_never_starts_process(tmp_path,monkeypatch):
    monkeypatch.setattr(runner,'check_stage_b_readiness',lambda *a:{'ready':False,'blockers':['assets missing']})
    monkeypatch.setattr(runner.subprocess,'run',lambda *a,**k:pytest.fail('must not execute'))
    with pytest.raises(ValueError,match='assets missing'):
        runner.run(tmp_path,tmp_path/'absent.json')

@pytest.mark.parametrize('bad_shape',[False,True])
def test_preflight_loads_model_and_rejects_shape(tmp_path,monkeypatch,bad_shape):
    import hashlib
    import sys
    from verification import stage_b_preflight as module
    modelpath=tmp_path/'model.h5';modelpath.write_bytes(b'fixture only')
    sha=hashlib.sha256(modelpath.read_bytes()).hexdigest()
    metadata=tmp_path/'results/clean';metadata.mkdir(parents=True)
    (metadata/'cnn_baseline_metadata.json').write_text(json.dumps({'model_sha256':sha}))
    calls=[]
    def load(path):
        calls.append(path)
        return SimpleNamespace(input_shape=(None,128,128,3),output_shape=(None,9 if bad_shape else 10))
    fake=SimpleNamespace(__version__='2.21.0',keras=SimpleNamespace(models=SimpleNamespace(load_model=load),backend=SimpleNamespace(clear_session=lambda:None)))
    monkeypatch.setitem(sys.modules,'tensorflow',fake)
    monkeypatch.setitem(sys.modules,'keras',SimpleNamespace(__version__='3.15.1'))
    monkeypatch.setattr(module.sys,'version_info',(3,11))
    contract={'models':[{'id':'cnn_baseline','path':'model.h5','sha256':sha,'input_shape':[128,128,3]}]}
    if bad_shape:
        with pytest.raises(ValueError,match='shape'):module.preflight(tmp_path,contract)
    else:
        result=module.preflight(tmp_path,contract)
        assert result['models_loaded']==['cnn_baseline']
        assert result['inference_performed'] is False
    assert calls==[modelpath]


@pytest.mark.parametrize('method',['gaussian','mean'])
def test_defense_csv_tamper_rejected(tmp_path,method):
    import csv
    for folder in ['configs','results','web/maris/public/evidence']:
        shutil.copytree(ROOT/folder,tmp_path/folder)
    p=tmp_path/f'results/defenses/experimental/{method}_run_01/cnn_eps_0.03_samples.csv'
    rows=runner.read_rows(p)
    row=rows[0]
    row['adaptive_defended_pred']=str((int(row['true_index'])+1)%10) if row['adaptive_defended_pred']==row['true_index'] else row['true_index']
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    with pytest.raises(ValueError,match='defense CSV to summary'):
        check(tmp_path)


def test_keyboard_interrupt_is_not_running(tmp_path,monkeypatch):
    monkeypatch.setattr(runner.platform,'platform',lambda:'test')
    root=tmp_path/'repo';root.mkdir()
    contract=json.loads((ROOT/'configs/stage_b_verification_contract.json').read_text())
    contract['outputs']['run_id']='interrupted'
    path=tmp_path/'contract.json';path.write_text(json.dumps(contract))
    monkeypatch.setattr(runner,'check_stage_b_readiness',lambda *a:{'ready':True,'blockers':[]})
    def interrupt(cmd,**kw):
        if 'freeze' in cmd:return SimpleNamespace(stdout='test')
        raise KeyboardInterrupt()
    monkeypatch.setattr(runner.subprocess,'run',interrupt)
    with pytest.raises(KeyboardInterrupt):runner.run(root,path)
    report=json.loads((tmp_path/'stage-b-interrupted/rerun-report.json').read_text())
    assert report['status']=='INTERRUPTED'
    assert report['comparisons']==[]


@pytest.mark.parametrize('versions',[((3,12),'2.21.0','3.15.1'),((3,11),'2.20.0','3.15.1'),((3,11),'2.21.0','3.14.0')])
def test_preflight_rejects_wrong_runtime(versions):
    from verification.stage_b_preflight import validate_versions
    with pytest.raises(ValueError):validate_versions(*versions)


def test_preflight_accepts_documented_runtime():
    from verification.stage_b_preflight import validate_versions
    validate_versions((3,11),'2.21.0','3.15.1')
