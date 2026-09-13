"""Fixed, differentiable 3x3 binomial Gaussian smoothing baseline.

Input: normalized NHWC float images. No resizing, learned weights or tuning.
Do not apply to rendered comparison PNG panels as if they were raw attacks.
"""
from __future__ import annotations

import math
import numpy as np

KERNEL = ((1., 2., 1.), (2., 4., 2.), (1., 2., 1.))


def gaussian_numpy(images):
    """Independent NumPy reference; never use inside a gradient attack."""
    x = np.asarray(images)
    if not np.issubdtype(x.dtype, np.floating):
        raise ValueError("images must be floating point in [0, 1]")
    if x.ndim != 4 or min(x.shape) < 1 or min(x.shape[1:3]) < 2:
        raise ValueError("expected nonempty NHWC, height/width >= 2")
    if not np.isfinite(x).all() or np.any(x < 0) or np.any(x > 1):
        raise ValueError("images must be finite and in [0, 1]")
    x = x.astype(np.float32)
    padded = np.pad(x, ((0, 0), (1, 1), (1, 1), (0, 0)), mode="reflect")
    out = np.zeros_like(x)
    for i in range(3):
        for j in range(3):
            out += (KERNEL[i][j] / 16.) * padded[:, i:i+x.shape[1], j:j+x.shape[2], :]
    return out


def gaussian_tensorflow(images):
    """True TensorFlow gradient, reflect edges, independent color channels."""
    import tensorflow as tf
    x = tf.convert_to_tensor(images)
    if not x.dtype.is_floating:
        raise ValueError("images must be floating point in [0, 1]")
    tf.debugging.assert_rank(x, 4)
    tf.debugging.assert_positive(tf.shape(x))
    tf.debugging.assert_greater_equal(tf.shape(x)[1:3], 2)
    tf.debugging.assert_all_finite(x, "non-finite image")
    tf.debugging.assert_greater_equal(x, tf.cast(0, x.dtype))
    tf.debugging.assert_less_equal(x, tf.cast(1, x.dtype))
    x = tf.cast(x, tf.float32)
    kernel = tf.reshape(tf.constant(KERNEL, tf.float32) / 16., (3, 3, 1, 1))
    kernel = tf.tile(kernel, [1, 1, tf.shape(x)[-1], 1])
    return tf.nn.depthwise_conv2d(
        tf.pad(x, [[0, 0], [1, 1], [1, 1], [0, 0]], mode="REFLECT"),
        kernel, strides=[1, 1, 1, 1], padding="VALID")


class GaussianDefendedModel:
    """Inference-only wrapper sharing the original model, without compilation."""
    def __init__(self, model):
        self.model = model

    def __call__(self, images, training=False):
        if training is not False:
            raise ValueError("experimental defense is inference-only")
        return self.model(gaussian_tensorflow(images), training=False)


def generate_adaptive_fgsm(model, images, labels, epsilon):
    """Untargeted FGSM on f(D(x)); budget measured on x_adv - x BEFORE D.

    Reuses the canonical attack unchanged. Returns attacked inputs, not D(x_adv).
    """
    import tensorflow as tf
    from adversarial_ai.attacks.fgsm import generate_fgsm, infer_from_logits
    if isinstance(epsilon, bool) or not math.isfinite(float(epsilon)) or not 0 <= epsilon <= 1:
        raise ValueError("epsilon must be finite in [0, 1]")
    labels = tf.convert_to_tensor(labels, dtype=tf.float32)
    tf.debugging.assert_rank(labels, 2)
    tf.debugging.assert_equal(tf.shape(labels)[0], tf.shape(images)[0])
    tf.debugging.assert_all_finite(labels, "non-finite labels")
    tf.debugging.assert_equal(labels, tf.round(labels))
    tf.debugging.assert_greater_equal(labels, 0.)
    tf.debugging.assert_less_equal(labels, 1.)
    tf.debugging.assert_equal(tf.reduce_sum(labels, axis=1), 1.)
    attacked = generate_fgsm(GaussianDefendedModel(model), images, labels, epsilon,
                             from_logits=infer_from_logits(model))
    tf.debugging.assert_all_finite(attacked, "non-finite attack")
    tf.debugging.assert_less_equal(tf.reduce_max(tf.abs(attacked - tf.cast(images, tf.float32))), epsilon + 1e-6)
    return attacked
