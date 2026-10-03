import numpy as np
import pytest
from adversarial_ai.attacks.square import square_linf
from adversarial_ai.evaluation.square_evaluation import summarize


def scores(x):
    v=x[:,0,0,0]-.5
    return np.stack([v,-v],axis=1)


def test_actual_success_budget_and_bounds():
    x=np.full((12,8,8,1),.51,dtype=np.float32)
    original=x.copy()
    calls=[]
    def counted(z):
        calls.append(len(z));return scores(z)
    r=square_linf(counted,x,np.zeros(12,dtype=int),epsilon=.1,max_queries=40)
    assert np.any(r.predictions!=0)
    assert sum(calls)==r.queries.sum()
    assert r.queries.max()<=40
    assert np.max(np.abs(r.adversarial-x))<=.100001
    assert r.adversarial.min()>=0 and r.adversarial.max()<=1
    np.testing.assert_array_equal(x,original)
    np.testing.assert_array_equal(r.predictions,scores(r.adversarial).argmax(1))


@pytest.mark.parametrize('epsilon,budget',[(0,20),(.1,1)])
def test_no_attack(epsilon,budget):
    x=np.full((2,4,4,1),.51,dtype=np.float32)
    r=square_linf(scores,x,np.array([0,1]),epsilon=epsilon,max_queries=budget)
    np.testing.assert_array_equal(r.adversarial,x)
    assert r.queries.tolist()==[1,1]


def test_wrong_clean_and_tie_are_not_false_success():
    x=np.full((2,4,4,1),.5,dtype=np.float32)
    r=square_linf(lambda z:np.ones((len(z),2)),x,np.array([0,1]),max_queries=7)
    assert r.predictions.tolist()==[0,0]
    assert r.queries.tolist()==[7,1]
    np.testing.assert_array_equal(r.adversarial,x)


def test_seed_and_global_rng():
    x=np.full((4,5,6,3),.51,dtype=np.float32)
    y=np.zeros(4,dtype=int)
    np.random.seed(123);expected=np.random.random()
    np.random.seed(123)
    a=square_linf(scores,x,y,max_queries=8)
    assert np.random.random()==expected
    b=square_linf(scores,x,y,max_queries=8)
    np.testing.assert_array_equal(a.adversarial,b.adversarial)
    np.testing.assert_array_equal(a.queries,b.queries)


@pytest.mark.parametrize('kwargs',[{'epsilon':-1},{'epsilon':float('nan')},
    {'max_queries':0},{'max_queries':True},{'p_init':0},{'seed':-1}])
def test_bad_settings(kwargs):
    with pytest.raises(ValueError):
        square_linf(scores,np.ones((1,4,4,1),np.float32),np.array([0]),**kwargs)


def test_bad_outputs_and_labels():
    x=np.ones((1,4,4,1),np.float32)
    for model,y in [(lambda z:np.full((len(z),2),np.nan),np.array([0])),
                    (scores,np.array([2])),(scores,np.array([.1]))]:
        with pytest.raises(ValueError):square_linf(model,x,y)


def test_asr_excludes_wrong_clean_and_counts_success_queries():
    rows=[dict(true_index=0,clean_pred=0,attacked_pred=1,queries=3),
          dict(true_index=0,clean_pred=0,attacked_pred=0,queries=10),
          dict(true_index=0,clean_pred=1,attacked_pred=1,queries=1)]
    m=summarize(rows,10)
    assert m['asr']==.5 and m['asr_denominator']==2
    assert m['attacked_correct']==1 and m['mean_success_queries']==3
    assert m['success_by_total_queries']=={'1':0,'10':1}
