from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from adversarial_ai.evaluation import defense_evaluation as ev


def frame():
    return pd.DataFrame(dict(relative_path=['A/a','A/b','B/c','B/d'],epsilon=[.01]*4,
        true_index=[0,0,1,1],clean_pred=[0,1,1,0],defended_clean_pred=[0,0,0,0],
        attacked_pred=[1,0,1,1],transfer_defended_pred=[1,0,1,1],
        adaptive_defended_pred=[1,1,1,1],original_linf=[.01]*4,adaptive_linf=[.01]*4))


def test_pipeline_denominators_and_harm_are_separate():
    r=ev.summarize(frame())
    assert r['asr_original']==dict(successes=1,denominator=2,asr=.5)
    assert r['asr_adaptive_defended']==dict(successes=2,denominator=2,asr=1.)
    assert r['clean_harmed']==1 and r['clean_recovered']==1
    assert r['common_clean_correct']['attacked']['denominator']==1
    assert ev.summarize(frame().iloc[2:])['asr_adaptive_defended']['asr'] is None
    assert ev.summarize(frame().iloc[:0])['accuracy']['clean'] is None


@pytest.mark.parametrize('column,value',[('clean_pred',1),('true_index',1),('adaptive_linf',float('nan')),
    ('original_linf',.02),('epsilon',.03),('relative_path','wrong'),('attacked_pred',.5)])
def test_row_mutation_fails(column,value):
    f=frame(); canonical=f[['relative_path','true_index','clean_pred']].rename(columns={'clean_pred':'predicted_index'})
    f[column]=f[column].astype(object); f.loc[0,column]=value
    with pytest.raises((ValueError,TypeError)):
        ev.validate_rows(f,canonical,canonical.relative_path,.01,2)


def test_zero_invariants_allow_defense_clean_change():
    f=frame();f['epsilon']=0.;f['original_linf']=0.;f['adaptive_linf']=0.
    f['attacked_pred']=f.clean_pred; f['transfer_defended_pred']=f.defended_clean_pred
    f['adaptive_defended_pred']=f.defended_clean_pred
    c=f[['relative_path','true_index','clean_pred']].rename(columns={'clean_pred':'predicted_index'})
    ev.validate_rows(f,c,c.relative_path,0.,2)
    f.loc[0,'adaptive_defended_pred']=1
    with pytest.raises(ValueError,match='zero'):
        ev.validate_rows(f,c,c.relative_path,0.,2)


def test_no_overwrite_or_repository_outputs(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    for p in [repo,repo/'results',tmp_path]:
        with pytest.raises(ValueError): ev.prepare_output(p,repo)
    output=ev.prepare_output(tmp_path/'experiment',repo)
    sentinel=output/'keep';sentinel.write_text('keep')
    with pytest.raises(FileExistsError): ev.prepare_output(output,repo)
    assert sentinel.read_text()=='keep'


def test_full_orchestration_synthetic_assets(tmp_path,monkeypatch):
    tf=pytest.importorskip('tensorflow')
    from PIL import Image
    repo=tmp_path/'repo';repo.mkdir();monkeypatch.chdir(repo)
    (repo/'configs').mkdir();(repo/'models').mkdir();(repo/'results/clean').mkdir(parents=True)
    (repo/'configs/classes.json').write_text(json.dumps({'0':'A','1':'B'}))
    (repo/'configs/test_manifest.json').write_text('{}')
    for label in ['A','B']:
        (repo/'data/test'/label).mkdir(parents=True)
        Image.fromarray(np.full((3,3,3),128,np.uint8)).save(repo/'data/test'/label/'a.png')
    model=tf.keras.Sequential([tf.keras.Input((3,3,3)),tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(2,activation='softmax',kernel_initializer='zeros',
                              bias_initializer=tf.keras.initializers.Constant([1.,0.]))])
    model.save(repo/'models/test.h5')
    pd.DataFrame(dict(relative_path=['A/a.png','B/a.png'],true_index=[0,1],predicted_index=[0,0])).to_csv(
        repo/'results/clean/test.csv',index=False)
    monkeypatch.setattr(ev,'MODELS',(('test','models/test.h5',3,'test.csv'),))
    # ONLY this synthetic orchestration test substitutes canonical 781-image integrity;
    # real CLI cannot disable the production validator.
    calls=[]
    monkeypatch.setattr(ev,'validate_reproducibility_manifest',lambda **kwargs:calls.append(kwargs))
    out=tmp_path/'out'; ev.run(out)
    assert len(calls)==2
    assert json.loads((out/'COMPLETE.json').read_text())['promoted'] is False
    checks=json.loads((out/'SHA256.json').read_text())
    assert all(ev.sha256_file(out/k)==v for k,v in checks.items())
    summaries=json.loads((out/'summary.json').read_text())
    assert len(summaries)==4
    assert summaries[0]['overall']['samples']==2
    assert summaries[0]['overall']['asr_original']['asr']==0
    assert not (out/'FAILED.json').exists()
    # Canonical disagreement must never emit a completion marker.
    path=repo/'results/clean/test.csv';f=pd.read_csv(path);f.loc[0,'predicted_index']=1;f.to_csv(path,index=False)
    failed=tmp_path/'failed'
    with pytest.raises(ValueError,match='canonical'):
        ev.run(failed)
    assert (failed/'FAILED.json').is_file()
    assert not (failed/'COMPLETE.json').exists()
