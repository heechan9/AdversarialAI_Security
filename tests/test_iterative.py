import numpy as np
import pytest
from adversarial_ai.attacks.iterative import generate_iterative, validate_settings
from adversarial_ai.evaluation.iterative_evaluation import metrics, reserve_output, PIPELINES

@pytest.fixture
def model():
    import tensorflow as tf
    x=tf.keras.Input((2,2,1));z=tf.keras.layers.Flatten()(x)
    y=tf.keras.layers.Dense(2,activation='softmax',kernel_initializer=tf.keras.initializers.Constant([[1.,-1.]]*4))(z)
    return tf.keras.Model(x,y)


def inputs():
    return np.full((2,2,2,1),.5,np.float32),np.array([[1.,0.],[1.,0.]],np.float32)

@pytest.mark.parametrize('attack',['bim','pgd'])
def test_zero_identity_and_weights(model,attack):
    x,y=inputs();weights=[v.numpy().copy() for v in model.weights]
    z=generate_iterative(model,x,y,0,step_size=.03,steps=3,attack=attack)
    np.testing.assert_array_equal(x,z)
    for a,b in zip(weights,model.weights):np.testing.assert_array_equal(a,b.numpy())

def test_bim_analytic_projection_and_fgsm(model):
    from adversarial_ai.attacks.fgsm import generate_fgsm
    x,y=inputs()
    one=generate_iterative(model,x,y,.1,step_size=.1,steps=1,attack='bim')
    np.testing.assert_allclose(one,generate_fgsm(model,x,y,.1),atol=1e-7)
    many=generate_iterative(model,x,y,.1,step_size=.04,steps=10,attack='bim')
    np.testing.assert_allclose(many,.4,atol=1e-7)

@pytest.mark.parametrize('attack',['bim','pgd'])
def test_bounds_and_repeatability(model,attack):
    x,y=inputs();x[0]=.01;x[1]=.99
    kw=dict(step_size=.09,steps=4,attack=attack,restarts=1 if attack=='bim' else 3,seed=9)
    a=generate_iterative(model,x,y,.1,**kw);b=generate_iterative(model,x,y,.1,**kw)
    np.testing.assert_array_equal(a,b)
    assert np.max(abs(a.numpy()-x))<=.100001 and a.numpy().min()>=0 and a.numpy().max()<=1

@pytest.mark.parametrize('method',['gaussian','mean'])
def test_differentiable_defense_budget(model,method):
    from adversarial_ai.defenses.gaussian import GaussianDefendedModel
    from adversarial_ai.defenses.mean import MeanDefendedModel
    wrapper=GaussianDefendedModel if method=='gaussian' else MeanDefendedModel
    x,y=inputs();z=generate_iterative(wrapper(model),x,y,.1,step_size=.04,steps=5,attack='bim',from_logits=False)
    np.testing.assert_allclose(z,.4,atol=1e-6)

@pytest.mark.parametrize('field,value',[('epsilon',float('nan')),('epsilon',-1),('epsilon',True),('step_size',0),('step_size',float('inf')),('steps',0),('steps',True),('restarts',0),('seed',-1),('attack','jsma')])
def test_invalid_settings(field,value):
    args=dict(epsilon=.1,step_size=.01,steps=10,restarts=1,seed=0,attack='pgd');args[field]=value
    with pytest.raises(ValueError):validate_settings(**args)

def test_asr_pipeline_specific_denominator():
    rows=[dict(true_index=0,clean_pred=0,defended_clean_pred=1,attacked_pred=1,transfer_defended_pred=1,adaptive_defended_pred=1),dict(true_index=0,clean_pred=1,defended_clean_pred=0,attacked_pred=1,transfer_defended_pred=0,adaptive_defended_pred=1)]
    m=metrics(rows)
    assert m['attacked']['asr']==1 and m['transfer_defended']['asr']==0 and m['adaptive_defended']['asr']==1
    for r in rows:r['defended_clean_pred']=1
    assert metrics(rows)['adaptive_defended']['asr'] is None

def test_output_no_overwrite_or_traversal(tmp_path,monkeypatch):
    import adversarial_ai.evaluation.iterative_evaluation as ev
    monkeypatch.setattr(ev,'ROOT',tmp_path)
    monkeypatch.chdir(tmp_path)
    p=reserve_output('test');(p/'keep').write_text('original')
    with pytest.raises(FileExistsError):reserve_output('test')
    with pytest.raises(ValueError):reserve_output('../canonical')
    assert (p/'keep').read_text()=='original'

def test_invalid_inputs_fail(model):
    import tensorflow as tf
    x,y=inputs();x[0,0,0,0]=float('nan')
    with pytest.raises(tf.errors.InvalidArgumentError):generate_iterative(model,x,y,.1,step_size=.01,steps=1)

def test_missing_gradient_fails():
    import tensorflow as tf
    x,y=inputs()
    def constant(x,training=False):return tf.ones((tf.shape(x)[0],2))*.5
    with pytest.raises(RuntimeError):generate_iterative(constant,x,y,.1,step_size=.01,steps=1,from_logits=False)

def test_runner_synthetic_full_matrix(tmp_path,monkeypatch):
    import argparse,json,tensorflow as tf
    import adversarial_ai.evaluation.iterative_evaluation as ev
    monkeypatch.setattr(ev,'ROOT',tmp_path)
    monkeypatch.chdir(tmp_path)
    (tmp_path/'configs').mkdir()
    (tmp_path/'configs/classes.json').write_text(json.dumps({str(i):str(i) for i in range(10)}))
    (tmp_path/'configs/test_manifest.json').write_text('{}')
    monkeypatch.setattr(ev.subprocess,'check_output',lambda cmd,**kw:'a'*40 if 'rev-parse' in cmd else '')
    def validate(**kw):
        assert not kw['model_path'].is_absolute()
        assert kw['model_path'].as_posix().startswith('models/')
        return 'b'*64
    monkeypatch.setattr(ev,'validate_reproducibility_manifest',validate)
    class Generator:
        class_indices={str(i):i for i in range(10)}
        filenames=[f'0/{i}.png' for i in range(781)]
        def __len__(self):return 1
        def __getitem__(self,index):
            return np.full((781,2,2,1),.5,np.float32),np.eye(10,dtype=np.float32)[np.zeros(781,dtype=int)]
    monkeypatch.setattr(tf.keras.preprocessing.image.ImageDataGenerator,'flow_from_directory',lambda *a,**kw:Generator())
    def load(*a,**kw):
        x=tf.keras.Input((2,2,1));y=tf.keras.layers.Dense(10,activation='softmax',kernel_initializer='ones')(tf.keras.layers.Flatten()(x));return tf.keras.Model(x,y)
    monkeypatch.setattr(tf.keras.models,'load_model',load)
    args=argparse.Namespace(attack='bim',steps=1,step_size=.005,restarts=1,seed=0,batch_size=781,run_id='synthetic',data_dir=tmp_path/'data')
    out=ev.run(args);report=json.loads((out/'run.json').read_text())
    assert report['status']=='COMPLETED_NOT_INDEPENDENT_APPROVAL'
    assert len(report['conditions'])==16
    for c in report['conditions']:
        assert c['samples']==781 and c['metrics']['clean']['accuracy']==1
        assert len((out/c['csv']).read_text().splitlines())==782
    import hashlib
    candidate=tmp_path/'best.keras';candidate.write_bytes(b'synthetic loader fixture')
    args.trained_model=candidate;args.trained_model_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest();args.trained_model_kind='cnn'
    args.run_id='trained'
    trained=ev.run(args);trained_report=json.loads((trained/'run.json').read_text())
    assert len(trained_report['conditions'])==8 and trained_report['scope']['models']==['cnn']
    assert all(c['model_sha256']==args.trained_model_sha256 for c in trained_report['conditions'])
    args.run_id='bad-identity';args.trained_model_sha256='0'*64
    with pytest.raises(ValueError,match='identity'):ev.run(args)
    args.trained_model=args.trained_model_sha256=args.trained_model_kind=None
    args.run_id='failed'
    monkeypatch.setattr(ev,'validate_reproducibility_manifest',lambda **kw:(_ for _ in ()).throw(ValueError('hash mismatch')))
    with pytest.raises(ValueError,match='hash mismatch'):ev.run(args)
    fail=json.loads((tmp_path/'results/extensions/iterative/failed/run.json').read_text())
    assert fail['status']=='ERROR' and not fail['conditions']
