import numpy as np
import pytest
pytest.importorskip('torch')
from adversarial_ai.attacks.surfree_adapter import attack_one,load_official


class RepeatedOracle:
    def __init__(self,**kwargs):pass
    def __call__(self,oracle,x,labels,starting_points,**kwargs):
        for _ in range(100):oracle(starting_points)
        raise AssertionError('budget did not stop upstream')


def test_counts_all_queries_and_only_returns_observed_adversarial():
    calls=[]
    def predict(x):
        calls.append(x.copy());return (x[:,0,0,0]<.5).astype(int)
    x=np.full((8,8,3),.51,np.float32)
    r=attack_one(predict,x,0,RepeatedOracle,max_queries=12,classes=2)
    assert len(calls)==r['queries']==12
    assert r['successful'] and r['stop_reason']=='query_budget_reached'
    distances=[np.linalg.norm(z[0]-x) for z in calls if z[0,0,0,0]<.5]
    assert r['l2']==pytest.approx(min(distances))


def test_initialization_failure_is_not_robustness_certificate():
    r=attack_one(lambda x:np.zeros(len(x),dtype=int),np.full((4,4,3),.5,np.float32),0,
                 RepeatedOracle,max_queries=300,classes=2)
    assert r['queries']==201 and r['initialization_queries']==200
    assert r['stop_reason']=='initialization_failed' and not r['successful']
    assert r['l2']==0 and r['attacked_pred']==r['clean_pred']


def test_wrong_clean_costs_one_and_uses_no_attack():
    r=attack_one(lambda x:np.ones(len(x),dtype=int),np.full((4,4,3),.5,np.float32),0,
                 RepeatedOracle,classes=2)
    assert r['queries']==1 and not r['successful'] and r['l2']==0


def test_rejects_unpinned_source(tmp_path):
    (tmp_path/'surfree.py').write_text('invalid')
    with pytest.raises(ValueError,match='hash mismatch'):load_official(tmp_path)


def test_reproducible_seed():
    fn=lambda x:(x[:,0,0,0]<.5).astype(int)
    x=np.full((8,8,3),.51,np.float32)
    assert attack_one(fn,x,0,RepeatedOracle,max_queries=12,classes=2)==attack_one(fn,x,0,RepeatedOracle,max_queries=12,classes=2)


def test_rejects_score_vector_in_top1_interface():
    with pytest.raises(ValueError,match='integer label'):
        attack_one(lambda x:np.ones((len(x),2)),np.full((4,4,3),.5,np.float32),0,
                   RepeatedOracle,classes=2)
