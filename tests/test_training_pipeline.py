import hashlib,json,sys
import pytest
import verification.run_training_pipeline as runner


def setup_pipeline(tmp_path,monkeypatch):
    repo=tmp_path/'repo';(repo/'verification').mkdir(parents=True)
    prepared=tmp_path/'prepared';(prepared/'images/A').mkdir(parents=True)
    image=prepared/'images/A/one.jpg';image.write_bytes(b'fixture')
    (prepared/'preparation.json').write_text(json.dumps({'status':'PREPARED_EXACT_AUDIT_ONLY',
        'source_count':8067,'retained_count':1}))
    (prepared/'split-audit.json').write_text(json.dumps({'splits':{'train':[{
        'path':'A/one.jpg','sha256':hashlib.sha256(b'fixture').hexdigest()}]}}))
    monkeypatch.setattr(runner,'__file__',str(repo/'verification/run_training_pipeline.py'))
    monkeypatch.setattr(sys,'argv',['pipeline','--model','cnn','--prepared',str(prepared),
        '--valid',str(tmp_path/'valid'),'--test',str(tmp_path/'test'),'--run-prefix','fixture'])
    return repo,prepared,image


def test_changed_preparation_cannot_launch_training(tmp_path,monkeypatch):
    repo,prepared,image=setup_pipeline(tmp_path,monkeypatch);image.write_bytes(b'changed')
    calls=[];monkeypatch.setattr(runner.subprocess,'run',lambda *a,**k:calls.append(a))
    with pytest.raises(ValueError,match='training image changed'):runner.main()
    assert calls==[]
    assert not (repo/'results').exists()


def test_failed_training_cannot_reach_test_evaluation(tmp_path,monkeypatch):
    repo,prepared,image=setup_pipeline(tmp_path,monkeypatch);calls=[]
    def failed_training(*args,**kwargs):
        calls.append(args)
        output=repo/'results/extensions/adversarial_training/fixture-cnn';output.mkdir(parents=True)
        (output/'training.json').write_text(json.dumps({'status':'ERROR'}))
    monkeypatch.setattr(runner.subprocess,'run',failed_training)
    with pytest.raises(ValueError,match='training completion'):runner.main()
    assert len(calls)==1
    state=json.loads((repo/'results/extensions/pipelines/fixture-cnn/pipeline.json').read_text())
    assert state['status']=='ERROR'
