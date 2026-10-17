"""Synthetic runtime contracts; no private images or saved metrics are changed."""
import numpy as np
import pytest

from adversarial_ai.attacks.validated_fgsm import generate_fgsm


@pytest.mark.parametrize('epsilon', [float('nan'), float('inf'), -float('inf'),
                                    True, False, np.bool_(True), -0.01, 1.01,
                                    '0.1', None, [0.1], np.array(0.1)])
def test_invalid_epsilon_fails_before_model_call(epsilon):
    def forbidden(*args, **kwargs):
        pytest.fail('invalid settings must not call model')
    with pytest.raises(ValueError, match='epsilon'):
        generate_fgsm(forbidden, None, None, epsilon)


@pytest.mark.parametrize('kwargs', [{'targeted': 1}, {'targeted': 'false'},
                                    {'from_logits': 0}, {'from_logits': 'false'}])
def test_invalid_mode_flags(kwargs):
    with pytest.raises(ValueError, match='boolean'):
        generate_fgsm(None, None, None, 0.1, **kwargs)


@pytest.fixture
def tf():
    return pytest.importorskip('tensorflow')


@pytest.fixture
def inputs():
    return np.full((2, 2, 2, 1), .5, np.float32), np.eye(2, dtype=np.float32)


def linear_model(tf):
    def model(images, training=False):
        value = tf.reduce_sum(images, axis=(1, 2, 3))
        return tf.stack([value, -value], axis=1)
    return model


@pytest.mark.parametrize('images', [np.zeros((2, 2, 1)), np.zeros((0, 2, 2, 1)),
    np.zeros((2, 0, 2, 1)), np.zeros((2, 2, 0, 1)), np.zeros((2, 2, 2, 0)),
    np.full((2, 2, 2, 1), -.1), np.full((2, 2, 2, 1), 1.1),
    np.full((2, 2, 2, 1), np.nan), np.full((2, 2, 2, 1), np.inf)])
def test_invalid_images_even_at_zero_epsilon(tf, inputs, images):
    _, labels = inputs
    with pytest.raises((ValueError, tf.errors.InvalidArgumentError)):
        generate_fgsm(linear_model(tf), images, labels, 0., from_logits=True)


@pytest.mark.parametrize('labels', [np.array([0, 1]), np.eye(3, dtype=np.float32),
    np.zeros((2, 0)), np.ones((2, 1)), np.zeros((2, 2)), np.ones((2, 2)),
    np.full((2, 2), .5), np.array([[-1., 2.], [0., 1.]]),
    np.array([[np.nan, 0.], [0., 1.]]), np.array([[np.inf, 0.], [0., 1.]])])
@pytest.mark.parametrize('targeted', [False, True])
def test_invalid_true_labels(tf, inputs, labels, targeted):
    images, valid_labels = inputs
    with pytest.raises((ValueError, tf.errors.InvalidArgumentError)):
        generate_fgsm(linear_model(tf), images, labels, .1, from_logits=True,
                      targeted=targeted, target_labels=valid_labels if targeted else None)


@pytest.mark.parametrize('targets', [np.array([0, 1]), np.eye(3), np.zeros((2, 2)),
    np.ones((2, 2)), np.full((2, 2), .5), np.array([[1., 0., 0.], [0., 1., 0.]]),
    np.array([[np.nan, 0.], [0., 1.]]), np.array([[np.inf, 0.], [0., 1.]])])
def test_invalid_target_labels(tf, inputs, targets):
    images, labels = inputs
    with pytest.raises((ValueError, tf.errors.InvalidArgumentError)):
        generate_fgsm(linear_model(tf), images, labels, .1, from_logits=True,
                      targeted=True, target_labels=targets)


@pytest.mark.parametrize('shape', [(2,), (1, 2), (2, 3), (2, 1, 2)])
def test_invalid_prediction_shape(tf, inputs, shape):
    images, labels = inputs
    with pytest.raises((ValueError, tf.errors.InvalidArgumentError)):
        generate_fgsm(lambda x, training=False: tf.zeros(shape), images, labels,
                      .1, from_logits=True)


@pytest.mark.parametrize('bad', [np.nan, np.inf, -np.inf])
def test_nonfinite_predictions(tf, inputs, bad):
    images, labels = inputs
    def model(x, training=False):
        return linear_model(tf)(x) * tf.constant(bad, tf.float32)
    with pytest.raises(tf.errors.InvalidArgumentError, match='predictions must be finite'):
        generate_fgsm(model, images, labels, .1, from_logits=True)


@pytest.mark.parametrize('bad', [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize('epsilon', [0., .1])
def test_nonfinite_gradient_with_finite_predictions(tf, inputs, bad, epsilon):
    images, labels = inputs
    @tf.custom_gradient
    def corrupt_backward(x):
        def grad(dy):
            return tf.fill(tf.shape(x), tf.constant(bad, tf.float32))
        return x, grad
    def model(x, training=False):
        return linear_model(tf)(corrupt_backward(x))
    with pytest.raises(tf.errors.InvalidArgumentError, match='input gradient must be finite'):
        generate_fgsm(model, images, labels, epsilon, from_logits=True)


def test_missing_gradient_fails(tf, inputs):
    images, labels = inputs
    with pytest.raises(RuntimeError, match='input gradient'):
        generate_fgsm(lambda x, training=False: tf.ones((2, 2)), images, labels,
                      .1, from_logits=True)


@pytest.mark.parametrize('epsilon', [0, .1, 1., np.float32(.1), np.float64(.1)])
@pytest.mark.parametrize('targeted', [False, True])
def test_valid_analytic_direction_and_scalar_types(tf, inputs, epsilon, targeted):
    images, labels = inputs
    # Same labels for both modes make sign reversal directly observable.
    actual = generate_fgsm(linear_model(tf), images, labels, epsilon,
                          targeted=targeted, target_labels=labels if targeted else None,
                          from_logits=True).numpy()
    direction = np.array([-1., 1.], dtype=np.float32)[:, None, None, None]
    if targeted:
        direction = -direction
    expected = np.clip(images + float(epsilon) * direction, 0., 1.)
    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(images, np.full_like(images, .5))


def test_one_pixel_images_remain_supported(tf):
    images = np.full((1, 1, 1, 1), .5, np.float32)
    actual = generate_fgsm(linear_model(tf), images, [[1., 0.]], .1, from_logits=True)
    np.testing.assert_array_equal(actual.numpy(), np.full_like(images, .4))


@pytest.mark.parametrize('jit_compile', [False, True])
def test_outer_graph_execution_fails_closed_before_model_call(tf, inputs, jit_compile):
    calls = []
    def model(images, training=False):
        calls.append(True)
        return linear_model(tf)(images)
    @tf.function(jit_compile=jit_compile)
    def attack(images, labels):
        return generate_fgsm(model, images, labels, .1, from_logits=True)
    images, labels = inputs
    with pytest.raises(ValueError, match='requires eager execution'):
        attack(images, labels)
    assert not calls


@pytest.mark.parametrize('jit_compile', [False, True])
def test_eager_api_accepts_compiled_model_forward(tf, inputs, jit_compile):
    images, labels = inputs
    model = tf.function(linear_model(tf), jit_compile=jit_compile)
    actual = generate_fgsm(model, images, labels, .1, from_logits=True)
    expected = images + np.array([-.1, .1], np.float32)[:, None, None, None]
    np.testing.assert_array_equal(actual.numpy(), expected)


@pytest.mark.parametrize('jit_compile', [False, True])
def test_eager_api_checks_gradients_of_compiled_model(tf, inputs, jit_compile):
    images, labels = inputs
    @tf.custom_gradient
    def corrupt_backward(x):
        return x, lambda dy: tf.fill(tf.shape(x), tf.constant(float('nan')))
    @tf.function(jit_compile=jit_compile)
    def model(images, training=False):
        return linear_model(tf)(corrupt_backward(images))
    with pytest.raises(tf.errors.InvalidArgumentError, match='input gradient must be finite'):
        generate_fgsm(model, images, labels, .1, from_logits=True)


@pytest.mark.parametrize('from_logits', [False, True])
@pytest.mark.parametrize('defense', ['none', 'gaussian', 'mean'])
@pytest.mark.parametrize('targeted', [False, True])
@pytest.mark.parametrize('epsilon', [0., .01, .03, .05, 1.])
def test_exact_canonical_equivalence(tf, from_logits, defense, targeted, epsilon):
    from adversarial_ai.attacks.fgsm import generate_fgsm as canonical_fgsm
    from adversarial_ai.defenses.gaussian import GaussianDefendedModel
    from adversarial_ai.defenses.mean import MeanDefendedModel

    x = np.random.default_rng(123).uniform(0, 1, (3, 3, 3, 2)).astype(np.float32)
    x[0, 0, 0] = [0., 1.]
    labels = tf.one_hot([0, 1, 2], 3)
    targets = tf.one_hot([1, 2, 0], 3) if targeted else None
    inputs = tf.keras.Input((3, 3, 2))
    scores = tf.keras.layers.Dense(
        3, activation='linear' if from_logits else 'softmax',
        kernel_initializer=tf.keras.initializers.Constant(
            np.linspace(-.7, .8, 54, dtype=np.float32).reshape(18, 3)),
        bias_initializer=tf.keras.initializers.Constant([.05, -.03, .02]))(
            tf.keras.layers.Flatten()(inputs))
    model = tf.keras.Model(inputs, scores)
    weights = [weight.numpy().copy() for weight in model.weights]
    inference = {'none': lambda value: value, 'gaussian': GaussianDefendedModel,
                 'mean': MeanDefendedModel}[defense](model)
    kwargs = dict(targeted=targeted, target_labels=targets,
                  from_logits=None if defense == 'none' else from_logits)
    expected = canonical_fgsm(inference, x, labels, epsilon, **kwargs)
    actual = generate_fgsm(inference, x, labels, epsilon, **kwargs)
    np.testing.assert_array_equal(actual.numpy(), expected.numpy())
    for before, after in zip(weights, model.weights):
        np.testing.assert_array_equal(before, after.numpy())


@pytest.mark.parametrize('scores', [[-.1, 1.1], [.2, .2], [0., 0.], [1., 1.]])
def test_probability_mode_rejects_nonprobability_outputs(tf, inputs, scores):
    images, labels = inputs
    def model(x, training=False):
        # Finite/differentiable, so rejection must come from probability checks.
        return tf.tile(tf.constant([scores]), [tf.shape(x)[0], 1]) + 0. * linear_model(tf)(x)
    with pytest.raises(tf.errors.InvalidArgumentError, match='probabilit'):
        generate_fgsm(model, images, labels, .1, from_logits=False)


@pytest.mark.parametrize('dtype_name', ['float16', 'bfloat16', 'float32', 'float64'])
def test_probability_tolerance_accepts_softmax_dtypes(tf, inputs, dtype_name):
    images, labels = inputs
    dtype = getattr(tf, dtype_name)
    def model(x, training=False):
        return tf.cast(tf.nn.softmax(linear_model(tf)(x), axis=1), dtype)
    actual = generate_fgsm(model, images, labels, .1, from_logits=False)
    assert np.isfinite(actual.numpy()).all()
    assert actual.shape == images.shape


@pytest.mark.parametrize('dtype_name,tolerance', [('float16', 1e-3), ('bfloat16', 1e-2),
                                                 ('float32', 1e-5), ('float64', 1e-5)])
def test_probability_sum_outside_dtype_tolerance_is_rejected(tf, inputs, dtype_name, tolerance):
    images, labels = inputs
    dtype = getattr(tf, dtype_name)
    def model(x, training=False):
        return tf.cast(tf.nn.softmax(linear_model(tf)(x), axis=1) * (1. - 4 * tolerance), dtype)
    with pytest.raises(tf.errors.InvalidArgumentError, match='probability rows must sum to one'):
        generate_fgsm(model, images, labels, .1, from_logits=False)


def test_finite_negative_unnormalized_logits_remain_supported(tf, inputs):
    images, labels = inputs
    def model(x, training=False):
        return linear_model(tf)(x) - 5.
    actual = generate_fgsm(model, images, labels, .1, from_logits=True)
    expected = images + np.array([-.1, .1], np.float32)[:, None, None, None]
    np.testing.assert_array_equal(actual.numpy(), expected)


def test_finite_zero_gradient_is_valid_identity(tf, inputs):
    images, labels = inputs
    def model(x, training=False):
        return 0. * linear_model(tf)(x)
    actual = generate_fgsm(model, images, labels, .1, from_logits=True)
    np.testing.assert_array_equal(actual.numpy(), images)
