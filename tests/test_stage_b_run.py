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


def _write_rows(path, rows):
    import csv
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


@pytest.mark.parametrize('method',['gaussian','mean'])
def test_comparator_real_saved_rows_pass(tmp_path,method):
    source=ROOT/f'results/defenses/experimental/{method}_run_01'
    output=tmp_path/method;shutil.copytree(source,output)
    contract=json.loads((ROOT/'configs/stage_b_verification_contract.json').read_text())
    result = runner.compare_outputs(ROOT,output,method,contract)
    assert result['rows_compared']==6248
    assert result['status']=='PASS'
    assert result['differences']==[]


@pytest.mark.parametrize('method',['gaussian','mean'])
def test_comparator_collects_multiple_prediction_differences_without_raising(tmp_path,method):
    # A prediction mismatch (a *_pred column) is an ordinary, comparable
    # rerun outcome -- unlike relative_path/true_index, it must be collected
    # rather than aborting the whole comparison at the first one.
    source=ROOT/f'results/defenses/experimental/{method}_run_01'
    output=tmp_path/method;shutil.copytree(source,output)
    contract=json.loads((ROOT/'configs/stage_b_verification_contract.json').read_text())
    file=output/'cnn_eps_0_samples.csv'
    rows=runner.read_rows(file)
    rows[0]['adaptive_defended_pred']=str((int(rows[0]['adaptive_defended_pred'])+1)%10)
    rows[1]['clean_pred']=str((int(rows[1]['clean_pred'])+1)%10)
    _write_rows(file, rows)

    result = runner.compare_outputs(ROOT,output,method,contract)

    assert result['status']=='FAIL'
    assert result['rows_compared']==6248
    fields = {(d['row_index'], d['field']) for d in result['differences']}
    assert (0,'adaptive_defended_pred') in fields
    assert (1,'clean_pred') in fields
    assert len(result['differences'])==2


@pytest.mark.parametrize('method',['gaussian','mean'])
@pytest.mark.parametrize('key',['relative_path','true_index'])
def test_comparator_sample_identity_mismatch_still_raises_immediately(tmp_path,method,key):
    # relative_path/true_index identify WHICH sample/ground-truth is being
    # compared, not how it was classified -- these must never be folded
    # into the collected prediction differences.
    source=ROOT/f'results/defenses/experimental/{method}_run_01'
    output=tmp_path/method;shutil.copytree(source,output)
    contract=json.loads((ROOT/'configs/stage_b_verification_contract.json').read_text())
    file=output/'cnn_eps_0_samples.csv'
    rows=runner.read_rows(file)
    if key=='true_index':
        rows[0][key]=str((int(rows[0][key])+1)%10)
    else:
        rows[0][key]='not/a/real/path.png'
    _write_rows(file, rows)

    with pytest.raises(ValueError,match='label/path mismatch'):
        runner.compare_outputs(ROOT,output,method,contract)


@pytest.mark.parametrize('method',['gaussian','mean'])
def test_comparator_corrupted_row_count_still_raises_immediately(tmp_path,method):
    source=ROOT/f'results/defenses/experimental/{method}_run_01'
    output=tmp_path/method;shutil.copytree(source,output)
    contract=json.loads((ROOT/'configs/stage_b_verification_contract.json').read_text())
    file=output/'cnn_eps_0_samples.csv'
    rows=runner.read_rows(file)
    _write_rows(file, rows[:-1])  # drop a row: 780 instead of 781

    with pytest.raises(ValueError,match='expected 781 rows'):
        runner.compare_outputs(ROOT,output,method,contract)


def test_comparator_metric_difference_in_summary_is_collected_not_raised(tmp_path):
    method='gaussian'
    source=ROOT/f'results/defenses/experimental/{method}_run_01'
    output=tmp_path/method;shutil.copytree(source,output)
    contract=json.loads((ROOT/'configs/stage_b_verification_contract.json').read_text())
    summary_path=output/'summary.json'
    summary=json.loads(summary_path.read_text())

    state = {'done': False}
    def bump_first_number(node):
        if state['done']:
            return node
        if isinstance(node, dict):
            return {k: bump_first_number(v) for k, v in node.items()}
        if isinstance(node, list):
            return [bump_first_number(v) for v in node]
        if isinstance(node, (int, float)) and not isinstance(node, bool):
            state['done'] = True
            return node + contract['comparison']['metric_abs_tolerance'] * 100
        return node

    summary = bump_first_number(summary)
    assert state['done'], 'fixture summary.json must contain a numeric field'
    summary_path.write_text(json.dumps(summary))

    result = runner.compare_outputs(ROOT,output,method,contract)

    assert result['status']=='FAIL'
    assert any(d.get('location','').startswith('summary') for d in result['differences'])


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


def test_run_continues_to_next_method_after_a_fail_comparison(tmp_path,monkeypatch):
    # A FAIL comparison on the first defense method (label/metric
    # differences, not a structural problem) must not stop the second
    # method from running: both subprocesses execute, both comparisons are
    # recorded, and only THEN does the overall run end FAIL with a raise
    # (i.e. a failing exit code from main()).
    monkeypatch.setattr(runner.platform,'platform',lambda:'test platform')
    root=tmp_path/'repo';root.mkdir()
    contract=json.loads((ROOT/'configs/stage_b_verification_contract.json').read_text())
    contract['outputs']['run_id']='fail-then-continue'
    path=tmp_path/'contract.json';path.write_text(json.dumps(contract))
    monkeypatch.setattr(runner,'check_stage_b_readiness',lambda *a:{'ready':True,'blockers':[]})

    def fake_run(cmd,**kw):
        if 'freeze' in cmd:return SimpleNamespace(stdout='mock environment\n')
        if 'verification.stage_b_preflight' in cmd:return SimpleNamespace(returncode=0)
        Path(cmd[-1]).mkdir()
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runner.subprocess,'run',fake_run)

    seen_methods=[]
    def fake_compare(root_,output_dir,method,contract_):
        seen_methods.append(method)
        if method=='gaussian':
            return {'method':method,'rows_compared':6248,'status':'FAIL',
                     'differences':[{'field':'clean_pred','row_index':0}]}
        return {'method':method,'rows_compared':6248,'status':'PASS','differences':[]}
    monkeypatch.setattr(runner,'compare_outputs',fake_compare)

    with pytest.raises(ValueError,match='differences'):
        runner.run(root,path)

    # Both methods ran -- the FAIL comparison did not abort the loop.
    assert seen_methods==['gaussian','mean']
    report=json.loads((tmp_path/'stage-b-fail-then-continue/rerun-report.json').read_text())
    assert report['status']=='FAIL'
    assert len(report['commands'])==3  # preflight + gaussian + mean, both defense subprocesses ran
    assert [c['method'] for c in report['comparisons']]==['gaussian','mean']
    assert report['comparisons'][0]['status']=='FAIL'
    assert report['comparisons'][1]['status']=='PASS'


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
