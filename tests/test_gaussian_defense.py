import numpy as np
import pytest
from adversarial_ai.defenses.gaussian import gaussian_numpy


def test_impulse_kernel_and_channels():
    x = np.zeros((1, 5, 5, 3), np.float32)
    x[0, 2, 2, 0] = 1
    out = gaussian_numpy(x)
    np.testing.assert_array_equal(out[0, 1:4, 1:4, 0],
                                  np.array([[1,2,1],[2,4,2],[1,2,1]]) / 16)
    assert not out[..., 1:].any()
    assert x.sum() == 1


def test_constant_edges_and_no_mutation():
    x = np.full((2, 2, 3, 3), .5, np.float32)
    before = x.copy()
    np.testing.assert_array_equal(gaussian_numpy(x), x)
    np.testing.assert_array_equal(x, before)


@pytest.mark.parametrize('x', [np.zeros((2,2,3)), np.zeros((0,2,2,3)),
    np.zeros((1,1,2,3)), np.full((1,2,2,3), np.nan),
    np.full((1,2,2,3), np.inf), np.full((1,2,2,3), -.1),
    np.full((1,2,2,3), 1.1), np.zeros((1,2,2,3), dtype=np.uint8)])
def test_reference_rejects_invalid(x):
    with pytest.raises(ValueError):
        gaussian_numpy(x)


def test_tensorflow_matches_reference_and_has_true_gradient():
    tf = pytest.importorskip('tensorflow')
    from adversarial_ai.defenses.gaussian import gaussian_tensorflow
    x = tf.constant(np.random.default_rng(3).uniform(.2, .8, (2,5,6,3)), tf.float32)
    with tf.GradientTape() as tape:
        tape.watch(x)
        out = gaussian_tensorflow(x)
        loss = out[0, 2, 2, 0]
    grad = tape.gradient(loss, x).numpy()
    np.testing.assert_allclose(out.numpy(), gaussian_numpy(x.numpy()), atol=1e-7)
    np.testing.assert_array_equal(grad[0,1:4,1:4,0],
                                  np.array([[1,2,1],[2,4,2],[1,2,1]]) / 16)
    np.testing.assert_allclose(tf.function(gaussian_tensorflow)(x), out, atol=1e-7)


def test_adaptive_fgsm_full_gradient_budget_zero_and_weights():
    tf = pytest.importorskip('tensorflow')
    from adversarial_ai.defenses.gaussian import GaussianDefendedModel, generate_adaptive_fgsm
    inp = tf.keras.Input((5,5,1))
    out = tf.keras.layers.Dense(2, activation='softmax',
        kernel_initializer=tf.keras.initializers.Constant(
            np.stack([np.arange(25)-12, 12-np.arange(25)], axis=1) / 25))(tf.keras.layers.Flatten()(inp))
    model = tf.keras.Model(inp, out)
    x = tf.constant(np.random.default_rng(4).uniform(.1,.9,(2,5,5,1)), tf.float32)
    y = tf.one_hot([0,1],2)
    before = [v.numpy().copy() for v in model.weights]
    wrapped = GaussianDefendedModel(model)
    with tf.GradientTape() as tape:
        tape.watch(x)
        loss = tf.reduce_mean(tf.keras.losses.categorical_crossentropy(y, wrapped(x)))
    g = tape.gradient(loss, x)
    assert np.isfinite(g).all() and np.any(g.numpy() != 0)
    for eps in [0., .01, .03, .05]:
        adv = generate_adaptive_fgsm(model, x, y, eps)
        np.testing.assert_allclose(adv, tf.clip_by_value(x + eps*tf.sign(g),0,1), atol=1e-7)
        assert np.max(np.abs(adv-x)) <= eps + 1e-6
        assert np.min(adv) >= 0 and np.max(adv) <= 1
        if eps == 0:
            np.testing.assert_array_equal(adv,x)
            np.testing.assert_array_equal(wrapped(adv),wrapped(x))
    for a,b in zip(before, model.weights):
        np.testing.assert_array_equal(a,b.numpy())
    for eps in [float('nan'), float('inf'), -.1, True]:
        with pytest.raises(ValueError):
            generate_adaptive_fgsm(model,x,y,eps)
    with pytest.raises(ValueError):
        wrapped(x, training=True)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -.01, 1.01])
def test_tensorflow_rejects_invalid_pixels(value):
    tf = pytest.importorskip('tensorflow')
    from adversarial_ai.defenses.gaussian import gaussian_tensorflow
    with pytest.raises(tf.errors.InvalidArgumentError):
        gaussian_tensorflow(tf.fill((1,2,2,3), value))


def test_adaptive_rejects_bad_labels_and_accepts_float64_input():
    tf = pytest.importorskip('tensorflow')
    from adversarial_ai.defenses.gaussian import generate_adaptive_fgsm
    model = tf.keras.Sequential([tf.keras.Input((2,2,1)),
        tf.keras.layers.Flatten(), tf.keras.layers.Dense(2, activation='softmax')])
    x = np.full((1,2,2,1), .5, dtype=np.float64)
    np.testing.assert_array_equal(generate_adaptive_fgsm(model,x,[[1.,0.]],0), x)
    for y in [[[.5,.5]], [[float('nan'),0.]], [[1.,1.]]]:
        with pytest.raises(tf.errors.InvalidArgumentError):
            generate_adaptive_fgsm(model,x,y,.01)
