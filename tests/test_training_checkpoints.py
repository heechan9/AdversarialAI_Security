import json
import numpy as np
import pytest
from adversarial_ai.training.checkpoints import save_snapshot, latest_snapshot


def test_optimizer_roundtrip_and_incomplete_latest(tmp_path):
    import tensorflow as tf
    tf.keras.utils.set_random_seed(17)
    model=tf.keras.Sequential([tf.keras.Input((2,)),tf.keras.layers.Dense(1)])
    model.compile(optimizer=tf.keras.optimizers.Adam(.01),loss='mse')
    x=np.array([[1.,2.],[3.,4.]],dtype='float32'); y=np.array([[1.],[0.]],dtype='float32')
    model.train_on_batch(x,y)
    best=tmp_path/'best.keras';model.save(best)
    identity={'source':'test','settings':{'batch':2}}
    state=dict(identity=identity,next_epoch=1,best_score=.5,report={'epochs':[{'epoch':1}]})
    first=save_snapshot(tmp_path/'checkpoints',model,best,state)
    state['next_epoch']=2;state['report']['epochs'].append({'epoch':2})
    broken=save_snapshot(tmp_path/'checkpoints',model,best,state)
    (broken/'last.keras').write_bytes(b'torn copy')
    folder,record=latest_snapshot(tmp_path/'checkpoints',identity)
    assert folder==first and record['next_epoch']==1
    restored=tf.keras.models.load_model(folder/'last.keras')
    assert int(restored.optimizer.iterations)==int(model.optimizer.iterations)
    for a,b in zip(restored.optimizer.variables,model.optimizer.variables):np.testing.assert_array_equal(a.numpy(),b.numpy())
    model.train_on_batch(x,y);restored.train_on_batch(x,y)
    for a,b in zip(model.get_weights(),restored.get_weights()):np.testing.assert_allclose(a,b,atol=1e-7)
    with pytest.raises(ValueError,match='No complete'):latest_snapshot(tmp_path/'checkpoints',{'source':'changed'})
