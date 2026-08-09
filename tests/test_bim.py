"""Unit tests for BIM attack. Uses a tiny synthetic model -- no real project
models or the 781-image dataset are loaded or evaluated here."""

import numpy as np
import pytest

tf = pytest.importorskip("tensorflow")

from adversarial_ai.attacks.bim import _project, generate_bim


NUM_CLASSES = 3
IMG_SHAPE = (8, 8, 3)


def _make_model(seed=0):
    tf.keras.utils.set_random_seed(seed)
    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=IMG_SHAPE),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(16, activation="relu"),
            tf.keras.layers.Dense(NUM_CLASSES, activation="softmax"),
        ]
    )
    return model


def _make_batch(n=4, seed=1):
    rng = np.random.default_rng(seed)
    images = rng.uniform(0.0, 1.0, size=(n, *IMG_SHAPE)).astype("float32")
    labels_idx = rng.integers(0, NUM_CLASSES, size=n)
    labels = tf.one_hot(labels_idx, NUM_CLASSES)
    return tf.constant(images), labels, labels_idx


def test_epsilon_zero_reproduces_clean():
    model = _make_model()
    images, labels, _ = _make_batch()
    clean_pred = model(images, training=False)

    x_adv = generate_bim(model, images, labels, epsilon=0.0, alpha=0.5, steps=5)

    np.testing.assert_allclose(x_adv.numpy(), images.numpy(), atol=1e-6)
    adv_pred = model(x_adv, training=False)
    np.testing.assert_allclose(adv_pred.numpy(), clean_pred.numpy(), atol=1e-6)


def test_linf_bound_respected():
    model = _make_model()
    images, labels, _ = _make_batch()
    epsilon = 0.03

    x_adv = generate_bim(model, images, labels, epsilon=epsilon, alpha=0.02, steps=10)

    linf = tf.reduce_max(tf.abs(x_adv - images)).numpy()
    assert linf <= epsilon + 1e-6


def test_pixel_range_respected():
    model = _make_model()
    images, labels, _ = _make_batch()

    x_adv = generate_bim(model, images, labels, epsilon=0.05, alpha=0.05, steps=10)

    assert tf.reduce_min(x_adv).numpy() >= 0.0 - 1e-6
    assert tf.reduce_max(x_adv).numpy() <= 1.0 + 1e-6


def test_project_helper_enforces_ball_and_pixel_range_directly():
    # Direct test of the per-step projection used inside every iteration,
    # not just an indirect check on the final output.
    x_orig = tf.constant([[0.5, 0.02, 0.98]])
    epsilon = 0.03
    # x is deliberately far outside both the epsilon-ball and [0, 1].
    x = tf.constant([[5.0, -3.0, 10.0]])

    projected = _project(x, x_orig, epsilon)

    delta = tf.abs(projected - x_orig).numpy()
    assert (delta <= epsilon + 1e-6).all()
    assert (projected.numpy() >= 0.0 - 1e-6).all()
    assert (projected.numpy() <= 1.0 + 1e-6).all()


def test_model_weights_unchanged():
    model = _make_model()
    images, labels, _ = _make_batch()
    weights_before = [w.numpy().copy() for w in model.weights]

    generate_bim(model, images, labels, epsilon=0.03, alpha=0.02, steps=10)

    for before, after in zip(weights_before, model.weights):
        np.testing.assert_array_equal(before, after.numpy())


def test_no_nan_or_inf_in_output():
    model = _make_model()
    images, labels, _ = _make_batch()

    x_adv = generate_bim(model, images, labels, epsilon=0.05, alpha=0.02, steps=10)

    assert not tf.reduce_any(tf.math.is_nan(x_adv)).numpy()
    assert not tf.reduce_any(tf.math.is_inf(x_adv)).numpy()


def test_untargeted_increases_true_label_loss():
    model = _make_model()
    images, labels, _ = _make_batch()
    loss_fn = tf.keras.losses.CategoricalCrossentropy()

    clean_pred = model(images, training=False)
    loss_before = loss_fn(labels, clean_pred).numpy()

    x_adv = generate_bim(model, images, labels, epsilon=0.05, alpha=0.02, steps=10)
    adv_pred = model(x_adv, training=False)
    loss_after = loss_fn(labels, adv_pred).numpy()

    assert loss_after > loss_before


def test_targeted_decreases_target_label_loss():
    model = _make_model()
    images, labels, labels_idx = _make_batch()
    # pick a target class different from the true label for every sample
    target_idx = (labels_idx + 1) % NUM_CLASSES
    target_labels = tf.one_hot(target_idx, NUM_CLASSES)
    loss_fn = tf.keras.losses.CategoricalCrossentropy()

    clean_pred = model(images, training=False)
    loss_before = loss_fn(target_labels, clean_pred).numpy()

    x_adv = generate_bim(
        model,
        images,
        labels,
        epsilon=0.05,
        alpha=0.02,
        steps=10,
        targeted=True,
        target_labels=target_labels,
    )
    adv_pred = model(x_adv, training=False)
    loss_after = loss_fn(target_labels, adv_pred).numpy()

    assert loss_after < loss_before


def test_targeted_without_target_labels_raises():
    model = _make_model()
    images, labels, _ = _make_batch()
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, epsilon=0.03, alpha=0.02, steps=5, targeted=True)


def test_target_labels_without_targeted_flag_raises():
    model = _make_model()
    images, labels, labels_idx = _make_batch()
    target_labels = tf.one_hot((labels_idx + 1) % NUM_CLASSES, NUM_CLASSES)
    with pytest.raises(ValueError):
        generate_bim(
            model,
            images,
            labels,
            epsilon=0.03,
            alpha=0.02,
            steps=5,
            target_labels=target_labels,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(epsilon=-0.01, alpha=0.02, steps=5),
        dict(epsilon=0.03, alpha=0.0, steps=5),
        dict(epsilon=0.03, alpha=-0.02, steps=5),
        dict(epsilon=0.03, alpha=0.02, steps=0),
        dict(epsilon=0.03, alpha=0.02, steps=-1),
    ],
)
def test_invalid_parameters_raise(kwargs):
    model = _make_model()
    images, labels, _ = _make_batch()
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, **kwargs)


def test_epsilon_zero_alpha_zero_allowed():
    # ε=0, α=0 must be accepted (this is the eps=0 sanity-check
    # configuration) and must reproduce clean predictions exactly.
    model = _make_model()
    images, labels, _ = _make_batch()
    clean_pred = model(images, training=False)

    x_adv = generate_bim(model, images, labels, epsilon=0.0, alpha=0.0, steps=5)

    np.testing.assert_allclose(x_adv.numpy(), images.numpy(), atol=1e-6)
    adv_pred = model(x_adv, training=False)
    np.testing.assert_allclose(adv_pred.numpy(), clean_pred.numpy(), atol=1e-6)


def test_epsilon_positive_alpha_zero_raises():
    # epsilon>0 with alpha=0 can never move inside the ball -- this is a
    # misconfiguration, not a valid "no-op" request, and must raise.
    model = _make_model()
    images, labels, _ = _make_batch()
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, epsilon=0.03, alpha=0.0, steps=5)


@pytest.mark.parametrize("bad_epsilon", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_epsilon_raises(bad_epsilon):
    model = _make_model()
    images, labels, _ = _make_batch()
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, epsilon=bad_epsilon, alpha=0.02, steps=5)


@pytest.mark.parametrize("bad_alpha", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_alpha_raises(bad_alpha):
    model = _make_model()
    images, labels, _ = _make_batch()
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, epsilon=0.03, alpha=bad_alpha, steps=5)


def test_epsilon_bool_rejected():
    # bool is a subclass of int/float-compatible in Python; True/False must
    # not silently pass as epsilon=1.0 / epsilon=0.0.
    model = _make_model()
    images, labels, _ = _make_batch()
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, epsilon=True, alpha=0.02, steps=5)
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, epsilon=False, alpha=0.02, steps=5)


def test_alpha_bool_rejected():
    model = _make_model()
    images, labels, _ = _make_batch()
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, epsilon=0.03, alpha=True, steps=5)
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, epsilon=0.03, alpha=False, steps=5)


def test_steps_bool_true_rejected():
    # bool is a subclass of int in Python; steps=True must not silently
    # pass as steps=1.
    model = _make_model()
    images, labels, _ = _make_batch()
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, epsilon=0.03, alpha=0.02, steps=True)


def test_steps_bool_false_rejected():
    model = _make_model()
    images, labels, _ = _make_batch()
    with pytest.raises(ValueError):
        generate_bim(model, images, labels, epsilon=0.03, alpha=0.02, steps=False)


def test_nan_weights_trigger_finite_check():
    # Force NaN into the model's own weights so the gradient becomes
    # non-finite, and confirm the attack surfaces this immediately via the
    # specific finite-check exception (tf.errors.InvalidArgumentError) --
    # not just "some exception or other" that could mask an unrelated bug.
    model = _make_model()
    images, labels, _ = _make_batch()
    weights = model.get_weights()
    weights[0][:] = np.nan
    model.set_weights(weights)

    with pytest.raises(tf.errors.InvalidArgumentError):
        generate_bim(model, images, labels, epsilon=0.03, alpha=0.02, steps=3)


def test_deterministic_no_random_start():
    # No random start means identical inputs must produce bit-identical
    # outputs across repeated runs.
    model = _make_model()
    images, labels, _ = _make_batch()

    x_adv_1 = generate_bim(model, images, labels, epsilon=0.03, alpha=0.02, steps=10)
    x_adv_2 = generate_bim(model, images, labels, epsilon=0.03, alpha=0.02, steps=10)

    np.testing.assert_array_equal(x_adv_1.numpy(), x_adv_2.numpy())
