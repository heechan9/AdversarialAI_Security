"""Targeted pairwise JSMA on probabilities with exact blockwise pair search.

L0 budget counts scalar channel features, not spatial RGB pixels. O(d^2)
search is intentionally explicit: no hidden top-k candidate approximation.
"""
import math
import numpy as np
from .fgsm import infer_from_logits


def select_pair(target_gradient, other_gradient, eligible, theta, block_size=256, changed=None, remaining=None):
    """Maximize -alpha*beta over all distinct eligible pairs, bounded memory."""
    a=np.asarray(target_gradient,dtype=np.float64).ravel()
    b=np.asarray(other_gradient,dtype=np.float64).ravel()
    e=np.asarray(eligible,dtype=bool).ravel()
    if a.shape!=b.shape or a.shape!=e.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('invalid saliency gradients')
    if type(block_size) is not int or block_size<1:raise ValueError('positive block size required')
    used=np.zeros_like(e) if changed is None else np.asarray(changed,dtype=bool).ravel()
    if used.shape!=e.shape:raise ValueError("changed mask shape mismatch")
    indices=np.flatnonzero(e);best=None;best_score=-np.inf
    for start in range(0,len(indices),block_size):
        left=indices[start:start+block_size]
        for second in range(start,len(indices),block_size):
            right=indices[second:second+block_size]
            alpha=a[left,None]+a[right];beta=b[left,None]+b[right]
            valid=(left[:,None]<right[None,:]) & ((alpha>0)&(beta<0) if theta>0 else (alpha<0)&(beta>0))
            if remaining is not None:
                valid &= ((~used[left,None]).astype(int)+(~used[right]).astype(int)<=remaining)
            scores=np.where(valid,-alpha*beta,-np.inf)
            pos=np.unravel_index(np.argmax(scores),scores.shape)
            score=scores[pos];pair=(int(left[pos[0]]),int(right[pos[1]]))
            if score>best_score or (np.isfinite(score) and score==best_score and (best is None or pair<best)):
                best_score=score;best=pair
    return best


def generate_jsma(model,image,target,*,theta=0.1,gamma=0.01,max_steps=100,from_logits=None,block_size=256):
    """One NHWC sample; returns image plus budget/termination metadata.

    Stop at target, budget exhaustion, no feasible pair, or iteration cap.
    A step cap is NOT equivalent to exhausting the attack budget.
    """
    import tensorflow as tf
    if isinstance(theta,bool) or not math.isfinite(theta) or not 0<abs(theta)<=1:raise ValueError('theta must be nonzero in [-1,1]')
    if isinstance(gamma,bool) or not math.isfinite(gamma) or not 0<=gamma<=1:raise ValueError('gamma in [0,1] required')
    if type(target) is not int or target<0 or type(max_steps) is not int or max_steps<1:raise ValueError('invalid target/steps')
    x=np.asarray(image,dtype=np.float32)
    if x.ndim!=4 or x.shape[0]!=1 or min(x.shape)<1 or not np.isfinite(x).all() or x.min()<0 or x.max()>1:raise ValueError('one finite NHWC image in [0,1] required')
    z=x.copy();budget=int(math.floor(gamma*x[0].size));steps=0;reason='step_limit'
    if from_logits is None:from_logits=infer_from_logits(model)
    def probs(t):
        values=model(t,training=False)
        if from_logits:values=tf.nn.softmax(values,axis=1)
        tf.debugging.assert_all_finite(values,'nonfinite model output')
        tf.debugging.assert_rank(values,2);tf.debugging.assert_equal(tf.shape(values)[0],1)
        tf.debugging.assert_greater_equal(values,0.);tf.debugging.assert_less_equal(values,1.)
        tf.debugging.assert_near(tf.reduce_sum(values,axis=1),tf.ones(1),atol=1e-5)
        if target>=int(tf.shape(values)[1]):raise ValueError('target out of class range')
        return values
    while steps<max_steps:
        t=tf.convert_to_tensor(z)
        with tf.GradientTape(persistent=True) as tape:
            tape.watch(t);values=probs(t);objective=values[0,target]
            other=tf.reduce_sum(values)-objective
        if int(tf.argmax(values[0]))==target:reason='target_reached';break
        a=tape.gradient(objective,t);b=tape.gradient(other,t);del tape
        if a is None or b is None:raise RuntimeError('JSMA input gradient unavailable')
        changed=(z!=x).ravel();remaining=budget-int(changed.sum())
        eligible=(z.ravel()<1) if theta>0 else (z.ravel()>0)
        pair=select_pair(a.numpy(),b.numpy(),eligible,theta,block_size,changed,remaining)
        if pair is None:reason='l0_budget' if remaining<2 else 'no_salient_pair';break
        flat=z.ravel();flat[list(pair)]=np.clip(flat[list(pair)]+theta,0,1);steps+=1
    success=int(tf.argmax(probs(tf.convert_to_tensor(z))[0]))==target
    if success:reason='target_reached'
    count=int(np.count_nonzero(z!=x))
    if count>budget:raise RuntimeError('L0 budget exceeded')
    return tf.convert_to_tensor(z),dict(target=target,target_success=success,steps=steps,termination=reason,
        changed_features=count,total_features=x[0].size,l0_fraction=count/x[0].size,budget_features=budget,
        variant='pairwise_probability_jsma',linf=float(np.max(np.abs(z-x))))
