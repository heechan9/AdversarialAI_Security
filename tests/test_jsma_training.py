import itertools,json
import numpy as np
import pytest
from adversarial_ai.attacks.jsma import select_pair,generate_jsma
from adversarial_ai.training.adversarial_training import train_batch,audit_splits


def make_model():
    import tensorflow as tf
    x=tf.keras.Input((2,2,1));y=tf.keras.layers.Dense(2,activation='softmax',kernel_initializer=tf.keras.initializers.Constant([[-1.,1.]]*4),bias_initializer=tf.keras.initializers.Constant([2.,0.]))(tf.keras.layers.Flatten()(x))
    return tf.keras.Model(x,y)

@pytest.mark.parametrize('theta',[.1,-.1])
@pytest.mark.parametrize('block',[1,2,5])
def test_pair_search_matches_bruteforce(theta,block):
    rng=np.random.default_rng(1);a=rng.normal(size=19);b=rng.normal(size=19);eligible=rng.random(19)>.2
    pairs=[]
    for i,j in itertools.combinations(np.flatnonzero(eligible),2):
        alpha=a[i]+a[j];beta=b[i]+b[j]
        if (alpha>0 and beta<0) if theta>0 else (alpha<0 and beta>0):pairs.append((-alpha*beta,(i,j)))
    expected=sorted(pairs,key=lambda x:(-x[0],x[1]))[0][1]
    assert select_pair(a,b,eligible,theta,block)==expected


def test_target_success_budget_and_weights():
    model=make_model();before=model.get_weights();x=np.zeros((1,2,2,1),np.float32)
    z,info=generate_jsma(model,x,1,theta=1.,gamma=.5,max_steps=3)
    assert info['target_success'] and info['changed_features']==2 and info['termination']=='target_reached'
    for a,b in zip(before,model.get_weights()):np.testing.assert_array_equal(a,b)
    z,info=generate_jsma(model,x,1,theta=.1,gamma=0,max_steps=3)
    np.testing.assert_array_equal(z,x);assert info['termination']=='l0_budget'


def test_step_limit_not_misreported_success():
    _,info=generate_jsma(make_model(),np.zeros((1,2,2,1),np.float32),1,theta=.01,gamma=1,max_steps=1)
    assert not info['target_success'] and info['termination']=='step_limit'


def test_repeat_feature_respects_unique_budget():
    _,info=generate_jsma(make_model(),np.zeros((1,2,2,1),np.float32),1,theta=.2,gamma=.5,max_steps=10)
    assert info['target_success'] and info['changed_features']==2 and info['steps']>1


def test_pgd_train_step_changes_clone_only():
    import tensorflow as tf
    source=make_model();original=source.get_weights();clone=tf.keras.models.clone_model(source);clone.set_weights(original)
    x=np.full((3,2,2,1),.2,np.float32);y=np.array([[0,1]]*3,np.float32)
    loss=train_batch(clone,tf.keras.optimizers.SGD(.1),x,y,epsilon=.1,step_size=.05,steps=2,seed=1)
    assert np.isfinite(loss) and any(not np.array_equal(a,b) for a,b in zip(original,clone.get_weights()))
    for a,b in zip(original,source.get_weights()):np.testing.assert_array_equal(a,b)


def make_splits(tmp_path):
    from PIL import Image
    import hashlib
    roots=[tmp_path/n for n in ['train','val','test']]
    for r in roots:(r/'A').mkdir(parents=True)
    Image.new('RGB',(2,2),(1,2,3)).save(roots[0]/'A/a.png')
    Image.new('RGB',(2,2),(4,5,6)).save(roots[1]/'A/a.png')
    rows=[]
    for i in range(781):
        p=roots[2]/f'A/{i}.png';Image.new('RGB',(2,2),(i%256,i//256,10)).save(p)
        rows.append(dict(relative_path=p.relative_to(roots[2]).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps(dict(test_samples=781,test_files=rows)))
    return roots,manifest


def test_split_audit_and_reencoded_overlap(tmp_path):
    from PIL import Image
    roots,manifest=make_splits(tmp_path)
    report=audit_splits(*roots,manifest,['A'])
    assert len(report['splits']['test'])==781 and report['near_duplicate_checked'] is False
    # Same decoded pixels in a different lossless format is still leakage.
    (roots[0]/'A/a.png').unlink()
    with Image.open(roots[2]/'A/0.png') as im:im.save(roots[0]/'A/copied.bmp')
    with pytest.raises(ValueError,match='overlap'):audit_splits(*roots,manifest,['A'])


def test_split_corruption_and_duplicates(tmp_path):
    roots,manifest=make_splits(tmp_path)
    (roots[0]/'A/dupe.png').write_bytes((roots[0]/'A/a.png').read_bytes())
    with pytest.raises(ValueError,match='duplicate'):audit_splits(*roots,manifest,['A'])
    (roots[0]/'A/dupe.png').unlink();(roots[2]/'A/0.png').write_bytes(b'corrupt')
    with pytest.raises(Exception):audit_splits(*roots,manifest,['A'])

@pytest.mark.parametrize('theta,gamma,steps',[(0,.1,2),(float('nan'),.1,2),(.1,-.1,2),(.1,.1,0)])
def test_invalid_jsma_parameters(theta,gamma,steps):
    with pytest.raises(ValueError):generate_jsma(make_model(),np.zeros((1,2,2,1),np.float32),1,theta=theta,gamma=gamma,max_steps=steps)


def test_training_cli_writes_separate_model(tmp_path,monkeypatch):
    import argparse,sys,hashlib
    import tensorflow as tf
    from PIL import Image
    import adversarial_ai.training.adversarial_training as tr
    root=tmp_path/'repo';(root/'src/adversarial_ai/training').mkdir(parents=True)
    monkeypatch.setattr(tr,'__file__',str(root/'src/adversarial_ai/training/adversarial_training.py'))
    monkeypatch.chdir(root)
    (root/'configs').mkdir();(root/'models').mkdir()
    names=[str(i) for i in range(10)]
    (root/'configs/classes.json').write_text(json.dumps({str(i):str(i) for i in range(10)}))
    for split,offset in [('train',20),('val',40)]:
        for i in range(10):
            d=root/split/str(i);d.mkdir(parents=True);Image.new('RGB',(2,2),(offset+i,100,100)).save(d/'a.png')
    test=root/'test/0';test.mkdir(parents=True);rows=[]
    for i in range(781):
        f=test/f'{i}.png';Image.new('RGB',(2,2),(i%256,i//256,10)).save(f)
        rows.append(dict(relative_path=f'0/{i}.png',sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
    x=tf.keras.Input((128,128,3));y=tf.keras.layers.Dense(10,activation='softmax')(tf.keras.layers.GlobalAveragePooling2D()(x))
    original=root/'models/cnn_baseline.h5';tf.keras.Model(x,y).save(original);original_hash=hashlib.sha256(original.read_bytes()).hexdigest()
    (root/'configs/test_manifest.json').write_text(json.dumps(dict(test_samples=781,test_files=rows,models=[dict(path='models/cnn_baseline.h5',sha256=original_hash)])))
    import subprocess
    monkeypatch.setattr(subprocess,'check_output',lambda cmd,**kw:'a'*40 if 'rev-parse' in cmd else '')
    monkeypatch.setattr(sys,'argv',['train','--model','cnn','--train-dir','train','--validation-dir','val','--test-dir','test','--epochs','2','--epsilon','0.01','--step-size','0.005','--steps','1','--batch-size','10','--run-id','synthetic'])
    actual_train_batch=tr.train_batch
    calls=[]
    def interrupt_second_epoch(*args,**kwargs):
        calls.append(1)
        if len(calls)==2:raise KeyboardInterrupt()
        return actual_train_batch(*args,**kwargs)
    monkeypatch.setattr(tr,'train_batch',interrupt_second_epoch)
    with pytest.raises(KeyboardInterrupt):tr.main()
    out=root/'results/extensions/adversarial_training/synthetic'
    report=json.loads((out/'training.json').read_text())
    assert report['status']=='INTERRUPTED' and report['best_epoch']==1
    assert hashlib.sha256(original.read_bytes()).hexdigest()==original_hash
    assert (out/'best.keras').is_file() and report['epochs'][0]['validation_samples']==10
    tf.keras.models.load_model(out/'best.keras',compile=False)
    # Simulate loss of the final report and restore from the completed epoch.
    before=(out/'best.keras').read_bytes()
    monkeypatch.setattr(sys,'argv',sys.argv+['--resume'])
    tr.main()
    resumed=json.loads((out/'training.json').read_text())
    assert resumed['status']=='TRAINED_NOT_TEST_EVALUATED'
    assert len(resumed['epochs'])==2 and len(resumed['resumptions'])==1
    assert len(calls)==3  # completed first epoch was not retrained
    assert hashlib.sha256(original.read_bytes()).hexdigest()==original_hash
