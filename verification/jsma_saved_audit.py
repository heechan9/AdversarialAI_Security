"""Check saved targeted JSMA evidence, without replaying neural inference."""
import argparse,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/'src'))
from adversarial_ai.evaluation.integrity import sha256_file


def audit(folder,root=ROOT):
    folder,root=Path(folder),Path(root)
    report=json.loads((folder/'run.json').read_text())
    manifest=root/'configs/test_manifest.json'
    assert report['kind']=='targeted_jsma_followup'
    assert report['manifest_sha256']==sha256_file(manifest)
    data=json.loads(manifest.read_text());settings=report['settings']
    assert settings['model'] in ('cnn','mobilenet')
    model='cnn_baseline.h5' if settings['model']=='cnn' else 'mobilenet_finetuned.h5'
    assert report['model_sha256']==next(x['sha256'] for x in data['models'] if x['path']=='models/'+model)
    assert settings['defense'] in ('none','gaussian','mean')
    assert report['attack_path']==('undefended' if settings['defense']=='none' else 'defense_aware')
    assert report['target_policy']=='(true_index + 1) % 10'
    assert report['l0_unit']=='scalar_channel_feature' and report['test_inventory']==781
    names=list(json.loads((root/'configs/classes.json').read_text()).values())
    ordered=sorted(data['test_files'],key=lambda x:x['relative_path'])
    rows=report['rows'];assert len(rows)==report['evaluated']<=settings['limit']<=781
    total=(128 if settings['model']=='cnn' else 224)**2*3
    assert 0<abs(settings['theta'])<=1 and 0<=settings['gamma']<=1 and settings['max_steps']>=1
    for row,source in zip(rows,ordered):
        assert row['relative_path']==source['relative_path']
        assert names[row['true_index']]==source['label']
        assert 0<=row['clean_pred']<10 and 0<=row['adversarial_pred']<10
        assert row['target']==(row['true_index']+1)%10
        assert row['variant']=='pairwise_probability_jsma'
        assert row['target_success']==(row['adversarial_pred']==row['target'])
        assert row['total_features']==total and row['budget_features']==math.floor(settings['gamma']*total)
        assert 0<=row['changed_features']<=min(row['budget_features'],2*row['steps'])
        assert 0<=row['steps']<=settings['max_steps']
        assert math.isfinite(row['linf']) and 0<=row['linf']<=1
        assert math.isclose(row['l0_fraction'],row['changed_features']/total,abs_tol=1e-12)
        assert row['termination'] in ('target_reached','l0_budget','no_salient_pair','step_limit')
        assert (row['termination']=='target_reached')==row['target_success']
        if row['termination']=='step_limit':assert row['steps']==settings['max_steps']
    full=report['status']=='FULL_COVERAGE_NOT_ROBUSTNESS_PROOF'
    if full:assert len(rows)==781
    eligible=[r for r in rows if r['clean_pred']==r['true_index']]
    success=sum(r['target_success'] for r in eligible)
    if report['status'] in ('FULL_COVERAGE_NOT_ROBUSTNESS_PROOF','PARTIAL_COVERAGE_NOT_FULL_EVALUATION'):
        assert report['asr_denominator']==len(eligible)
        assert report['targeted_asr_clean_correct']==(success/len(eligible) if eligible else None)
        assert report['accuracy']==sum(r['adversarial_pred']==r['true_index'] for r in rows)/len(rows)
        assert report['step_limited_samples']==sum(r['termination']=='step_limit' for r in rows)
    else:assert report['status'] in ('RUNNING','INTERRUPTED','ERROR')
    return dict(result='FULL_SAVED_EVIDENCE_CONSISTENT' if full else 'PARTIAL_SAVED_EVIDENCE_ONLY',
                report_sha256=sha256_file(folder/'run.json'),samples=len(rows),
                targeted_successes_clean_correct=success,asr_denominator=len(eligible),
                independent_verification_approval=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder',type=Path)
    print(json.dumps(audit(parser.parse_args().folder),indent=2))
