import numpy as np
import pytest

from adversarial_ai.evaluation.fgsm_evaluation import (
    compute_untargeted_asr,
    validate_reproducibility_manifest,
)


def _tensorflow():
    return pytest.importorskip("tensorflow")


def _model(tf):
    inputs = tf.keras.Input(shape=(2, 2, 1))
    flattened = tf.keras.layers.Flatten()(inputs)
    outputs = tf.keras.layers.Dense(
        2,
        activation="softmax",
        kernel_initializer=tf.keras.initializers.Constant(
            [[1.0, -1.0], [0.5, -0.5], [-0.5, 0.5], [-1.0, 1.0]]
        ),
        bias_initializer="zeros",
    )(flattened)
    return tf.keras.Model(inputs, outputs)


def test_asr_denominator_uses_only_clean_correct_samples():
    y_true = np.array([0, 0, 1, 1])
    clean_pred = np.array([0, 1, 1, 0])
    adversarial_pred = np.array([1, 0, 1, 1])
    asr, successes, denominator = compute_untargeted_asr(y_true, clean_pred, adversarial_pred)
    assert denominator == 2
    assert successes == 1
    assert asr == 0.5


def test_manifest_detects_model_hash_mismatch(tmp_path):
    import json

    model = tmp_path / "model.h5"
    model.write_bytes(b"actual model")
    manifest = {
        "test_samples": 781,
        "test_files": [{"relative_path": "A/a.jpg"}],
        "models": [{"path": model.as_posix(), "sha256": "0" * 64}],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256"):
        validate_reproducibility_manifest(path, model, ["A/a.jpg"])


def test_epsilon_zero_preserves_predictions_and_shape():
    tf = _tensorflow()
    from adversarial_ai.attacks.fgsm import generate_fgsm

    model = _model(tf)
    images = tf.constant([[[[0.2], [0.4]], [[0.6], [0.8]]]], dtype=tf.float32)
    labels = tf.one_hot([0], 2)
    clean_predictions = model(images, training=False)
    adversarial = generate_fgsm(model, images, labels, 0.0)
    adversarial_predictions = model(adversarial, training=False)
    np.testing.assert_array_equal(adversarial.numpy(), images.numpy())
    np.testing.assert_array_equal(
        tf.argmax(clean_predictions, axis=1).numpy(),
        tf.argmax(adversarial_predictions, axis=1).numpy(),
    )
    assert adversarial.shape == images.shape


def test_perturbation_bound_clipping_finiteness_and_weight_immutability():
    tf = _tensorflow()
    from adversarial_ai.attacks.fgsm import generate_fgsm

    model = _model(tf)
    images = tf.constant(
        [[[[0.0], [0.25]], [[0.75], [1.0]]], [[[0.1], [0.2]], [[0.3], [0.4]]]],
        dtype=tf.float32,
    )
    labels = tf.one_hot([0, 1], 2)
    weights_before = [value.numpy().copy() for value in model.weights]
    epsilon = 0.05
    adversarial = generate_fgsm(model, images, labels, epsilon)
    perturbation = np.abs(adversarial.numpy() - images.numpy())
    assert adversarial.shape == images.shape
    assert perturbation.max() <= epsilon + 1e-6
    assert adversarial.numpy().min() >= 0.0
    assert adversarial.numpy().max() <= 1.0
    assert np.isfinite(adversarial.numpy()).all()
    for before, after in zip(weights_before, model.weights):
        np.testing.assert_array_equal(before, after.numpy())


def test_targeted_attack_requires_target_labels():
    tf = _tensorflow()
    from adversarial_ai.attacks.fgsm import generate_fgsm

    model = _model(tf)
    images = tf.zeros((1, 2, 2, 1), dtype=tf.float32)
    labels = tf.one_hot([0], 2)
    with pytest.raises(ValueError, match="target_labels"):
        generate_fgsm(model, images, labels, 0.01, targeted=True)


def test_negative_epsilon_is_rejected():
    tf = _tensorflow()
    from adversarial_ai.attacks.fgsm import generate_fgsm

    model = _model(tf)
    images = tf.zeros((1, 2, 2, 1), dtype=tf.float32)
    labels = tf.one_hot([0], 2)
    with pytest.raises(ValueError, match="non-negative"):
        generate_fgsm(model, images, labels, -0.01)
