"""Independent arithmetic oracle and gradient/attack checks for the new filter."""
import numpy as np
import pytest
from adversarial_ai.defenses.mean import mean_numpy
from adversarial_ai.evaluation.mean_defense_evaluation import _defense_components


def test_mean_matches_explicit_neighborhoods_and_preserves_channels():
    x=np.random.default_rng(7).random((2,4,5,3),dtype=np.float32)
    padded=np.pad(x,((0,0),(1,1),(1,1),(0,0)),mode='reflect')
    expected=np.empty_like(x)
    for h in range(4):
        for w in range(5):
            expected[:,h,w,:]=padded[:,h:h+3,w:w+3,:].mean(axis=(1,2))
    np.testing.assert_allclose(mean_numpy(x),expected,atol=1e-7)
    constant=np.full((1,4,4,3),.5,np.float32)
    np.testing.assert_allclose(mean_numpy(constant),constant,atol=1e-7)


@pytest.mark.parametrize('bad',[np.zeros((1,3,3,1),np.uint8),np.full((1,3,3,1),np.nan),
    np.full((1,3,3,1),1.1),np.zeros((1,1,3,1)),np.zeros((0,3,3,1))])
def test_invalid_inputs_rejected(bad):
    with pytest.raises(ValueError): mean_numpy(bad)


def test_unknown_defense_rejected():
    with pytest.raises(ValueError,match='unknown'): _defense_components('typo')


def test_tensorflow_reference_gradient_and_adaptive_attack():
    tf=pytest.importorskip('tensorflow')
    from adversarial_ai.defenses.mean import mean_tensorflow, generate_adaptive_fgsm
    x=np.random.default_rng(21).uniform(.2,.8,(2,4,4,1)).astype('float32')
    np.testing.assert_allclose(mean_tensorflow(x),mean_numpy(x),atol=1e-7)
    v=tf.Variable(x)
    with tf.GradientTape() as tape:
        loss=tf.reduce_sum(mean_tensorflow(v)**2)
    grad=tape.gradient(loss,v).numpy()
    delta=np.zeros_like(x);delta[0,1,1,0]=1e-3
    finite=(np.sum(mean_numpy(x+delta)**2)-np.sum(mean_numpy(x-delta)**2))/(2e-3)
    np.testing.assert_allclose(grad[0,1,1,0],finite,rtol=.01,atol=.001)
    model=tf.keras.Sequential([tf.keras.Input((4,4,1)),tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(2,activation='softmax',kernel_initializer=tf.keras.initializers.RandomNormal(seed=4))])
    y=tf.one_hot([0,1],2)
    np.testing.assert_array_equal(generate_adaptive_fgsm(model,x,y,0),x)
    before=[w.numpy().copy() for w in model.weights]
    adv=generate_adaptive_fgsm(model,x,y,.03).numpy()
    assert np.isfinite(adv).all() and np.max(np.abs(adv-x))<=.03+1e-6
    assert np.any(adv!=x)
    for a,b in zip(before,model.weights): np.testing.assert_array_equal(a,b.numpy())
