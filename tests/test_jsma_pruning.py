"""Compare the accelerated selector against an independent exhaustive oracle."""
import itertools
import numpy as np
import pytest
from adversarial_ai.attacks.jsma import select_pair


def exhaustive(a,b,eligible,theta,changed,remaining):
    best=None;score=-np.inf
    for i,j in itertools.combinations(np.flatnonzero(eligible),2):
        if int(not changed[i])+int(not changed[j])>remaining:continue
        alpha=a[i]+a[j];beta=b[i]+b[j]
        valid=(alpha>0 and beta<0) if theta>0 else (alpha<0 and beta>0)
        if valid and -alpha*beta>score:
            best=(int(i),int(j));score=-alpha*beta
    return best


@pytest.mark.parametrize('theta',[1.,-1.])
@pytest.mark.parametrize('block_size',[1,4,256])
def test_pruning_matches_exhaustive_with_masks_and_ties(theta,block_size):
    rng=np.random.default_rng(2026)
    for trial in range(100):
        n=int(rng.integers(2,40));a=rng.normal(size=n);b=rng.normal(size=n)
        if trial%3==0:a=np.round(a);b=np.round(b)
        if trial%5==0:b=-a+rng.normal(0,1e-14,size=n)
        eligible=rng.random(n)>.2;changed=rng.random(n)>.5;remaining=trial%3
        expected=exhaustive(a,b,eligible,theta,changed,remaining)
        assert select_pair(a,b,eligible,theta,block_size,changed,remaining)==expected


def test_later_block_tie_retains_lexicographically_first_pair():
    a=np.array([1.,4.,4.,1.,4.]);b=-a
    assert select_pair(a,b,np.ones(5,bool),1.,2)==(1,2)


def test_empty_and_no_feasible_pairs():
    assert select_pair([],[],[],1.) is None
    assert select_pair([1,2],[1,2],[True,True],1.) is None


def test_overflow_keeps_original_block_traversal():
    a=np.array([-.2,1.,1.,1.])*1e200
    b=np.array([1.5,-1.,-1.,-3.])*1e200
    with np.errstate(over='ignore',invalid='ignore'):
        assert select_pair(a,b,np.ones(4,bool),1.,3)==(1,2)


def test_budget_shortcut_still_allows_repeated_features():
    a=np.array([1.,2.,3.]);b=-a;eligible=np.ones(3,bool)
    assert select_pair(a,b,eligible,1.,changed=np.zeros(3,bool),remaining=1) is None
    assert select_pair(a,b,eligible,1.,changed=np.array([False,False,True]),remaining=1)==(1,2)


@pytest.mark.parametrize('theta,target,start',[(.2,1,0.),(-.2,0,1.)])
def test_full_toy_attack_matches_exhaustive(monkeypatch,theta,target,start):
    import tensorflow as tf
    import adversarial_ai.attacks.jsma as jsma
    inputs=tf.keras.Input((2,2,1))
    outputs=tf.keras.layers.Dense(2,activation='softmax',
        kernel_initializer=tf.keras.initializers.Constant([[-1.,1.]]*4),
        bias_initializer=tf.keras.initializers.Constant([2.,0.]))(tf.keras.layers.Flatten()(inputs))
    model=tf.keras.Model(inputs,outputs);x=np.full((1,2,2,1),start,np.float32)
    actual,info=jsma.generate_jsma(model,x,target,theta=theta,gamma=.5,max_steps=10)
    def oracle(a,b,eligible,theta,block_size=256,changed=None,remaining=None):
        return exhaustive(np.asarray(a,dtype=np.float64).ravel(),np.asarray(b,dtype=np.float64).ravel(),
                          eligible,theta,changed,remaining)
    monkeypatch.setattr(jsma,'select_pair',oracle)
    expected,expected_info=jsma.generate_jsma(model,x,target,theta=theta,gamma=.5,max_steps=10)
    np.testing.assert_array_equal(actual.numpy(),expected.numpy())
    assert info==expected_info
