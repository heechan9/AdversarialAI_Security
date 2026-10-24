"""Synthetic-only tests; no private models, source images or real training runs."""
import copy
import hashlib
import json
import os

import numpy as np
import pytest

from adversarial_ai.training.controls import control_metadata, compare_controls
from verification.training_control_audit import audit


def batch():
    x=np.array([[[[.1],[.4]],[[.6],[.8]]],[[[.8],[.3]],[[.2],[.5]]]],np.float32)
    return x,np.eye(2,dtype=np.float32)


def model_and_calls():
    import tensorflow as tf
    calls=[]
    class Count(tf.keras.layers.Layer):
        def call(self,x,training=False):
            calls.append(training)
            return x
    x=tf.keras.Input((2,2,1))
    z=Count()(x)
    z=tf.keras.layers.BatchNormalization(momentum=.7)(z)
    z=tf.keras.layers.Flatten()(z)
    y=tf.keras.layers.Dense(2,activation='softmax',kernel_initializer=tf.keras.initializers.Constant([[.2,-.3]]*4))(z)
    model=tf.keras.Model(x,y);calls.clear()
    return model,calls


def test_clean_only_skips_attack_and_second_training_forward(monkeypatch):
    import tensorflow as tf
    import adversarial_ai.training.adversarial_training as tr
    model,calls=model_and_calls();reference,reference_calls=model_and_calls()
    reference.set_weights(model.get_weights());x,y=batch()
    def forbidden(*args,**kwargs):
        raise AssertionError('clean-only training must not generate adversarial inputs')
    monkeypatch.setattr(tr,'generate_iterative',forbidden)
    actual_optimizer=tf.keras.optimizers.Adam(.01)
    reference_optimizer=tf.keras.optimizers.Adam(.01)
    with tf.GradientTape() as tape:
        expected=tf.keras.losses.CategoricalCrossentropy()(y,reference(x,training=True))
    gradients=tape.gradient(expected,reference.trainable_variables)
    reference_optimizer.apply_gradients(zip(gradients,reference.trainable_variables))
    actual=tr.train_batch(model,actual_optimizer,x,y,epsilon=.03,step_size=.005,steps=7,seed=2026,clean_weight=1.)
    assert actual==float(expected)
    assert calls==[True] and reference_calls==[True]
    # Includes nontrainable BatchNorm moving mean/variance and optimizer slots.
    for a,b in zip(model.weights,reference.weights):np.testing.assert_array_equal(a.numpy(),b.numpy())
    for a,b in zip(actual_optimizer.variables,reference_optimizer.variables):np.testing.assert_array_equal(a.numpy(),b.numpy())


def test_default_mixed_step_is_numerically_unchanged(monkeypatch):
    import tensorflow as tf
    import adversarial_ai.training.adversarial_training as tr
    model,calls=model_and_calls();reference,reference_calls=model_and_calls()
    reference.set_weights(model.get_weights());x,y=batch();attack_calls=[]
    def attack(*args,**kwargs):
        attack_calls.append(kwargs)
        return tf.constant(x+.02)
    monkeypatch.setattr(tr,'generate_iterative',attack)
    optimizer=tf.keras.optimizers.Adam(.01);ref_optimizer=tf.keras.optimizers.Adam(.01)
    for _ in range(3):
        # Frozen pre-change 50:50 operation order, including both BN forwards.
        criterion=tf.keras.losses.CategoricalCrossentropy(from_logits=False)
        with tf.GradientTape() as tape:
            clean=criterion(y,reference(x,training=True))
            adv=criterion(y,reference(tf.stop_gradient(tf.constant(x+.02)),training=True))
            expected=.5*clean+(1-.5)*adv
            if reference.losses:expected+=tf.add_n(reference.losses)
        gradients=tape.gradient(expected,reference.trainable_variables)
        ref_optimizer.apply_gradients(zip(gradients,reference.trainable_variables))
        actual=tr.train_batch(model,optimizer,x,y,epsilon=.03,step_size=.005,steps=7,seed=2026)
        assert actual==float(expected)
        for a,b in zip(model.weights,reference.weights):np.testing.assert_array_equal(a.numpy(),b.numpy())
        for a,b in zip(optimizer.variables,ref_optimizer.variables):np.testing.assert_array_equal(a.numpy(),b.numpy())
    assert calls==reference_calls==[True]*6 and len(attack_calls)==3


@pytest.mark.parametrize('mutation',['multihot','soft_labels','wrong_classes','batch_mismatch',
    'negative_pixels','large_pixels','nan_pixels','nan_labels','empty','rank','wrong_input_shape',
    'epsilon','step_size','steps','seed'])
def test_clean_only_rejects_bad_inputs_before_state_mutation(monkeypatch,mutation):
    import tensorflow as tf
    import adversarial_ai.training.adversarial_training as tr
    model,calls=model_and_calls();optimizer=tf.keras.optimizers.Adam(.01)
    x,y=batch();kwargs=dict(epsilon=.03,step_size=.005,steps=7,seed=2026,clean_weight=1.)
    if mutation=='multihot':y[:]=1
    if mutation=='soft_labels':y[:]=.5
    if mutation=='wrong_classes':y=np.eye(3,dtype=np.float32)[:2]
    if mutation=='batch_mismatch':y=y[:1]
    if mutation=='negative_pixels':x[:]=-.5
    if mutation=='large_pixels':x[:]=1.1
    if mutation=='nan_pixels':x[0,0,0,0]=float('nan')
    if mutation=='nan_labels':y[0,0]=float('nan')
    if mutation=='empty':x=x[:0];y=y[:0]
    if mutation=='rank':x=x[0]
    if mutation=='wrong_input_shape':x=np.tile(x,(1,1,1,2))
    if mutation=='epsilon':kwargs['epsilon']=-1
    if mutation=='step_size':kwargs['step_size']=0
    if mutation=='steps':kwargs['steps']=0
    if mutation=='seed':kwargs['seed']=-1
    weights=[v.numpy().copy() for v in model.weights]
    opt_before=[v.numpy().copy() for v in optimizer.variables]
    monkeypatch.setattr(tr,'generate_iterative',lambda *a,**k:pytest.fail('attack called'))
    with pytest.raises((ValueError,tf.errors.InvalidArgumentError)):
        tr.train_batch(model,optimizer,x,y,**kwargs)
    assert calls==[] and int(optimizer.iterations)==0
    assert len(optimizer.variables)==len(opt_before)
    for a,b in zip(weights,model.weights):np.testing.assert_array_equal(a,b.numpy())
    for a,b in zip(opt_before,optimizer.variables):np.testing.assert_array_equal(a,b.numpy())


@pytest.mark.parametrize('name',['split-audit.json','training.json','training.json.tmp','best.keras'])
def test_training_write_guard_rejects_nonregular_leaf(tmp_path,name):
    from adversarial_ai.training.adversarial_training import validate_output_paths
    out=tmp_path/'run';out.mkdir();leaf=out/name
    leaf.mkdir();(leaf/'sentinel').write_bytes(b'unchanged')
    with pytest.raises(ValueError,match='nonregular'):validate_output_paths(out)
    assert (leaf/'sentinel').read_bytes()==b'unchanged'
    (leaf/'sentinel').unlink();leaf.rmdir()
    if hasattr(os,'mkfifo'):
        os.mkfifo(leaf)
        with pytest.raises(ValueError,match='nonregular'):validate_output_paths(out)
        leaf.unlink()


def test_training_write_guard_rejects_checkpoint_file(tmp_path):
    from adversarial_ai.training.adversarial_training import validate_output_paths
    out=tmp_path/'run';out.mkdir();(out/'checkpoints').write_bytes(b'unchanged')
    with pytest.raises(ValueError,match='checkpoints directory'):validate_output_paths(out)
    assert (out/'checkpoints').read_bytes()==b'unchanged'


def report(mode):
    value=dict(kind='adversarial_training_followup',status='TRAINED_NOT_TEST_EVALUATED',
        source_commit='a'*40,source_model_sha256='b'*64,split_audit_sha256='c'*64,
        tensorflow='2.21.0',keras='3.15.1',trained_model_sha256='d'*64,best_epoch=1,
        runtime=dict(python='3.12.14',numpy='2.3.5',platform='synthetic',numerical_environment={
            key:None for key in ('TF_ENABLE_ONEDNN_OPTS','TF_DETERMINISTIC_OPS','TF_NUM_INTRAOP_THREADS',
                                'TF_NUM_INTEROP_THREADS','OMP_NUM_THREADS','CUDA_VISIBLE_DEVICES')}),
        epochs=[dict(epoch=1,validation_pgd_accuracy=.5),dict(epoch=2,validation_pgd_accuracy=.5)],
        settings=dict(model='cnn',epochs=2,epsilon=.03,step_size=.005,steps=7,seed=2026,
                      batch_size=8,learning_rate=.00001,training_mode=mode,run_id=mode,
                      train_dir='/private/train',validation_dir='/private/valid',test_dir='/private/test'))
    value.update(control_metadata(value));return value


def test_pair_protocol_excludes_only_mode_and_execution_locations():
    a,b=report('clean_only'),report('pgd_mixed')
    b['settings']['train_dir']='/different/copy';b['settings']['run_id']='different'
    b.update(control_metadata(b))
    assert a['comparison_protocol_sha256']==b['comparison_protocol_sha256']
    assert compare_controls(a,b)==a['comparison_protocol']


@pytest.mark.parametrize('field,value',[('seed',2027),('batch_size',32),('epochs',3),('steps',20),('learning_rate',.01),('epsilon',.05)])
def test_pair_rejects_changed_settings(field,value):
    a,b=report('clean_only'),report('pgd_mixed')
    b['settings'][field]=value;b.update(control_metadata(b))
    with pytest.raises(ValueError):compare_controls(a,b)


@pytest.mark.parametrize('field,value',[('source_commit','e'*40),('source_model_sha256','e'*64),('split_audit_sha256','e'*64),('tensorflow','other'),('keras','other')])
def test_pair_rejects_changed_identity(field,value):
    a,b=report('clean_only'),report('pgd_mixed')
    b[field]=value;b.update(control_metadata(b))
    with pytest.raises(ValueError,match='protocols differ'):compare_controls(a,b)


def test_pair_rejects_runtime_drift_and_unknown_settings():
    a,b=report('clean_only'),report('pgd_mixed')
    b['runtime']['numerical_environment']['TF_ENABLE_ONEDNN_OPTS']='1'
    b.update(control_metadata(b))
    with pytest.raises(ValueError,match='protocols differ'):compare_controls(a,b)
    b['settings']['new_augmentation']='unreviewed'
    with pytest.raises(ValueError,match='schema'):control_metadata(b)


@pytest.mark.parametrize('key,value',[('epochs',True),('seed',-1),('epsilon',float('nan')),('step_size',0),('batch_size',False)])
def test_control_metadata_rejects_invalid_configuration(key,value):
    r=report('clean_only');r['settings'][key]=value
    with pytest.raises(ValueError):control_metadata(r)


@pytest.mark.parametrize('field,value',[('tensorflow',None),('tensorflow',''),('keras',None),('keras',''),
    ('run_id',None),('run_id','../unsafe'),('train_dir',None),('validation_dir','')])
def test_control_metadata_rejects_missing_identity_strings(field,value):
    r=report('clean_only')
    target=r if field in ('tensorflow','keras') else r['settings']
    target[field]=value
    with pytest.raises(ValueError):control_metadata(r)


@pytest.mark.parametrize('mutation',['mode','hash','weight','missing_epoch','tie','incomplete','same_mode','checkpoint','nan'])
def test_pair_rejects_inconsistent_or_partial_reports(mutation):
    a,b=report('clean_only'),report('pgd_mixed')
    if mutation=='mode':b['settings']['training_mode']='clean_only'
    if mutation=='hash':b['comparison_protocol_sha256']='0'*64
    if mutation=='weight':b['clean_weight']=1
    if mutation=='missing_epoch':b['epochs'].pop()
    if mutation=='tie':b['best_epoch']=2
    if mutation=='incomplete':b['status']='RUNNING'
    if mutation=='same_mode':b=copy.deepcopy(a)
    if mutation=='checkpoint':b.pop('trained_model_sha256')
    if mutation=='nan':b['epochs'][0]['validation_pgd_accuracy']=float('nan')
    with pytest.raises(ValueError):compare_controls(a,b)


def fixtures(tmp_path):
    roots=[]
    for mode in ('clean_only','pgd_mixed'):
        root=tmp_path/mode;root.mkdir();r=report(mode)
        for filename,key,content in [('best.keras','trained_model_sha256',mode.encode()),
                                     ('split-audit.json','split_audit_sha256',b'{"synthetic":true}')]:
            (root/filename).write_bytes(content);r[key]=hashlib.sha256(content).hexdigest()
        r.update(control_metadata(r));(root/'training.json').write_text(json.dumps(r));roots.append(root)
    return roots


def test_saved_pair_audit_and_checkpoint_tampering(tmp_path):
    a,b=fixtures(tmp_path)
    result=audit(a,b)
    assert result['result']=='PAIRED_RECORDED_PROTOCOL_AND_CHECKPOINTS_CONSISTENT'
    assert not result['test_evaluation_complete'] and not result['independent_verification_approval']
    (b/'best.keras').write_bytes(b'changed')
    with pytest.raises(ValueError,match='artifact identity'):audit(a,b)


def test_saved_pair_rejects_duplicate_json_and_shared_directory(tmp_path):
    a,b=fixtures(tmp_path)
    with pytest.raises(ValueError,match='distinct'):audit(a,a)
    (b/'training.json').write_text('{"status":"RUNNING","status":"TRAINED_NOT_TEST_EVALUATED"}')
    with pytest.raises(ValueError,match='duplicate JSON'):audit(a,b)
