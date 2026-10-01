"""Follow-up untargeted L-infinity BIM/PGD; canonical FGSM is untouched."""
import math
from .fgsm import infer_from_logits


def validate_settings(epsilon, step_size, steps, restarts, seed, attack):
    for name, value in [('epsilon', epsilon), ('step_size', step_size)]:
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError(f'{name} must be finite numeric')
    if not 0 <= epsilon <= 1 or not 0 < step_size <= 1:
        raise ValueError('epsilon in [0,1], step_size in (0,1] required')
    for value in (steps, restarts):
        if type(value) is not int or value < 1:
            raise ValueError('positive integer steps/restarts required')
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError('seed must be a nonnegative int32')
    if attack not in ('bim', 'pgd') or (attack == 'bim' and restarts != 1):
        raise ValueError('BIM uses one clean start; PGD uses random starts')


def generate_iterative(model, images, labels, epsilon, *, step_size, steps,
                       attack='pgd', restarts=1, seed=0, from_logits=None):
    """Return best candidate per sample, preferring misclassification then loss.

    Includes clean input and every iterate; stateless seeded random starts for
    PGD. Budget is measured before any differentiable defense wrapper.
    Seed reproducibility requires the same batch shape/order and environment.
    """
    validate_settings(epsilon, step_size, steps, restarts, seed, attack)
    import tensorflow as tf
    x=tf.convert_to_tensor(images, dtype=tf.float32)
    y=tf.convert_to_tensor(labels, dtype=tf.float32)
    tf.debugging.assert_rank(x,4);tf.debugging.assert_rank(y,2)
    tf.debugging.assert_positive(tf.shape(x))
    tf.debugging.assert_equal(tf.shape(x)[0],tf.shape(y)[0])
    for value in (x,y):
        tf.debugging.assert_all_finite(value,'nonfinite inputs')
        tf.debugging.assert_greater_equal(value,0.);tf.debugging.assert_less_equal(value,1.)
    tf.debugging.assert_equal(tf.reduce_sum(y,axis=1),tf.ones(tf.shape(y)[0]))
    tf.debugging.assert_equal(y,tf.round(y))
    if from_logits is None:from_logits=infer_from_logits(model)
    loss_fn=tf.keras.losses.CategoricalCrossentropy(from_logits=from_logits,reduction='none')
    def score(z):
        pred=model(z,training=False)
        tf.debugging.assert_equal(tf.shape(pred),tf.shape(y))
        tf.debugging.assert_all_finite(pred,'nonfinite predictions')
        losses=loss_fn(y,pred);tf.debugging.assert_all_finite(losses,'nonfinite losses')
        success=tf.not_equal(tf.argmax(pred,axis=1),tf.argmax(y,axis=1))
        return losses,success
    best=tf.identity(x);best_loss,best_success=score(best)
    if epsilon==0:return best
    lower=tf.maximum(0.,x-epsilon);upper=tf.minimum(1.,x+epsilon)
    def retain(z,best,best_loss,best_success):
        losses,success=score(z)
        take=(success & ~best_success) | ((success==best_success) & (losses>best_loss))
        return (tf.where(take[:,None,None,None],z,best),tf.where(take,losses,best_loss),tf.where(take,success,best_success))
    for restart in range(restarts):
        z=tf.identity(x)
        if attack=='pgd':
            noise=tf.random.stateless_uniform(tf.shape(x),seed=[seed,restart],minval=-epsilon,maxval=epsilon)
            z=tf.clip_by_value(x+noise,lower,upper)
        best,best_loss,best_success=retain(z,best,best_loss,best_success)
        for _ in range(steps):
            with tf.GradientTape() as tape:
                tape.watch(z)
                losses,_=score(z);loss=tf.reduce_mean(losses)
            gradient=tape.gradient(loss,z)
            if gradient is None:raise RuntimeError('input gradient unavailable')
            tf.debugging.assert_all_finite(gradient,'nonfinite gradient')
            z=tf.stop_gradient(tf.clip_by_value(z+step_size*tf.sign(gradient),lower,upper))
            best,best_loss,best_success=retain(z,best,best_loss,best_success)
    return tf.stop_gradient(best)
