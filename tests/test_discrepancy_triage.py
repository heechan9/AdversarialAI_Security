"""Regression and explicitly synthetic mutation tests; no inference fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from verification.discrepancy_triage import build, summarize

ROOT = Path(__file__).resolve().parents[1]
REPORT = 'results/verification/stage_b/hyeonsu_01_review/gaussian_differences.json'


def inputs():
    return (json.loads((ROOT/REPORT).read_text()),
            json.loads((ROOT/'configs/test_manifest.json').read_text())['test_files'],
            json.loads((ROOT/'configs/classes.json').read_text()))


def test_saved_totals_and_status():
    result = build(ROOT)
    assert result['totals'] == dict(compared_prediction_cells=62480, differing_prediction_cells=16, unique_affected_images=14)
    assert len(result['condition_groups']) == 80
    assert result['status_by_run'] == {'external-01': 'FAIL', 'pc-full-20260928': 'LOCAL_PASS'}
    assert result['discrepancy_state'] == {'cross-environment-01': 'open'}
    assert result['cause_status'] == 'UNRESOLVED'
    assert result['inference_performed'] is result['independent_reproduction'] is False
    assert sum(g['differing_prediction_cells'] for g in result['condition_groups']) == 16
    assert {d['model'] for d in result['cases']} == {'mobilenet'}
    for method, expected in [('gaussian', 10), ('mean', 6)]:
        assert sum(g['differing_prediction_cells'] for g in result['condition_groups'] if g['method'] == method) == expected


@pytest.mark.parametrize('filters,n', [({'model':'cnn'},0), ({'method':'gaussian'},10),
    ({'method':'mean'},6), ({'pipeline':'attacked'},4),
    ({'relative_path':'Bulkers/Bulkers_1039.jpeg'},2), ({'relative_path':'missing'},0),
    ({'method':'mean','pipeline':'attacked','relative_path':'Bulkers/Bulkers_1039.jpeg'},1)])
def test_filters_do_not_change_denominators(filters,n):
    baseline=build(ROOT); selected=build(ROOT, **filters)
    assert selected['totals'] == baseline['totals']
    assert selected['condition_groups'] == baseline['condition_groups']
    assert selected['affected_images'] == baseline['affected_images']
    assert len(selected['cases']) == selected['selection']['differing_prediction_cells'] == n


def test_trace_case():
    cases=build(ROOT,relative_path='Bulkers/Bulkers_1039.jpeg')['cases']
    assert len(cases)==2
    for d in cases:
        assert d['row_index']==99 and d['pipeline']=='attacked' and d['epsilon']=='0.03'
        assert (d['reference'],d['actual'],d['true_index']) == ('1','6','1')
        assert d['outcome']=='newly_incorrect'
        assert d['source_commit']=='491b973cd9f4840664044a83c0d62d1ee1bb98e8'
        assert all(len(d[k])==64 for k in ['reference_csv_sha256','actual_csv_sha256','evidence_sha256'])


@pytest.mark.parametrize('mutate',[
    lambda d:d['differences'].append(deepcopy(d['differences'][0])),
    lambda d:d['differences'][0].update(row_index=True),
    lambda d:d['differences'][0].update(row_index=-1),
    lambda d:d['differences'][0].update(relative_path='other.jpeg'),
    lambda d:d['differences'][0].update(true_index='0'),
    lambda d:d['differences'][0].update(actual='1'),
    lambda d:d['differences'][0].update(reference=1),
    lambda d:d['differences'][0].update(pipeline='unknown'),
    lambda d:d['differences'][0].update(file='cnn_eps_1_samples.csv'),
    lambda d:d['conditions'][5]['pipelines']['transfer_defended'].update(label_differences=2),
    lambda d:d['conditions'][5]['pipelines']['transfer_defended'].update(actual_correct=341),
    lambda d:d['conditions'][0]['pipelines']['clean'].update(reference_correct=True),
    lambda d:d['conditions'].append(deepcopy(d['conditions'][0])),
    lambda d:d.update(unique_affected_images=9),
    lambda d:d.update(inference_performed=True),
    lambda d:d['input_sha256'].pop('reference/cnn_eps_0_samples.csv'),
    lambda d:d['input_sha256'].update({'actual/cnn_eps_0_samples.csv':'no-hash'}),
])
def test_synthetic_inconsistent_records_rejected(mutate):
    doc,manifest,classes=inputs(); mutate(doc)
    with pytest.raises(ValueError): summarize(doc,'gaussian',manifest,classes)


def test_order_is_deterministic():
    doc,manifest,classes=inputs()
    expected=summarize(doc,'gaussian',manifest,classes)[0]
    doc['conditions'].reverse()
    assert summarize(doc,'gaussian',manifest,classes)[0] == expected
    assert json.dumps(build(ROOT),sort_keys=True) == json.dumps(build(ROOT),sort_keys=True)


def test_unknown_filter_rejected():
    with pytest.raises(ValueError): build(ROOT,model='not-a-model')


def test_cli_corruption_has_no_report(tmp_path):
    # Copy only the small checked public fixture subset, never private assets.
    for directory in ('verification','configs','results','docs'):
        shutil.copytree(ROOT/directory,tmp_path/directory,ignore=shutil.ignore_patterns('__pycache__'))
    p=tmp_path/REPORT;p.write_bytes(p.read_bytes()+b' ')
    result=subprocess.run([sys.executable,str(ROOT/'verification/discrepancy_triage.py'),'--repo-root',str(tmp_path)],capture_output=True,text=True)
    assert result.returncode==2 and result.stdout==''
    assert 'evidence changed' in result.stderr


def test_cli_read_only_and_json():
    files=[ROOT/'configs/test_manifest.json',ROOT/'results/verification/discrepancy_log.json',ROOT/REPORT]
    before=[p.read_bytes() for p in files]
    run=subprocess.run([sys.executable,str(ROOT/'verification/discrepancy_triage.py'),'--model','cnn'],capture_output=True,text=True)
    assert run.returncode==0 and json.loads(run.stdout)['cases']==[]
    assert before==[p.read_bytes() for p in files]
