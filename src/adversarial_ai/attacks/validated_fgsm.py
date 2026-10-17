"""Opt-in validated FGSM for new experiments.

The canonical ``attacks.fgsm`` source is hash-locked by historical evidence.
Keep it unchanged; callers explicitly import this module to use stricter
runtime validation while retaining the same valid-input FGSM calculation.
"""

from __future__ import annotations

import math
from numbers import Real
from typing import Any


from .fgsm import infer_from_logits


def generate_fgsm(
    model: Any,
    images: Any,
    labels: Any,
    epsilon: float,
    *,
    targeted: bool = False,
    target_labels: Any | None = None,
    from_logits: bool | None = None,
) -> Any:
    """Generate exactly one L-infinity FGSM step and clip it to ``[0, 1]``.

    Untargeted FGSM maximizes loss for the true labels. Targeted FGSM minimizes
    loss for ``target_labels``. Inputs and labels are expected to be batched;
    labels use the same one-hot format as the ship classifiers. Images must be
    nonempty NHWC tensors in [0, 1], and epsilon a finite real scalar in [0, 1].
    Malformed inputs, nonfinite model outputs/losses/gradients, and missing input
    gradients fail explicitly rather than producing invalid attack samples.
    Both true and target labels are validated in targeted mode. Zero epsilon
    retains the same model/gradient validation as a nonzero attack. Call this
    API eagerly, outside tf.function/XLA; compiled outer graphs may discard
    runtime assertions and are rejected before model execution.
    """
    if (isinstance(epsilon, bool) or not isinstance(epsilon, Real)
            or not 0 <= epsilon <= 1 or not math.isfinite(epsilon)):
        raise ValueError("epsilon must be a finite non-negative real scalar in [0, 1]")
    if type(targeted) is not bool:
        raise ValueError("targeted must be a boolean")
    if from_logits is not None and type(from_logits) is not bool:
        raise ValueError("from_logits must be a boolean or None")

    import tensorflow as tf

    if not tf.executing_eagerly():
        raise ValueError(
            "Validated FGSM requires eager execution; call it outside tf.function or XLA compilation"
        )

    images = tf.convert_to_tensor(images, dtype=tf.float32)
    tf.debugging.assert_rank(images, 4, message="images must be NHWC")
    tf.debugging.assert_positive(tf.shape(images), message="images must be nonempty")
    tf.debugging.assert_all_finite(images, "images must be finite")
    tf.debugging.assert_greater_equal(images, 0., message="images must be in [0, 1]")
    tf.debugging.assert_less_equal(images, 1., message="images must be in [0, 1]")

    def validate_labels(value, name):
        value = tf.convert_to_tensor(value, dtype=tf.float32)
        tf.debugging.assert_rank(value, 2, message=f"{name} must be one-hot [N, C]")
        tf.debugging.assert_equal(tf.shape(value)[0], tf.shape(images)[0],
                                  message=f"{name} batch size mismatch")
        tf.debugging.assert_greater_equal(tf.shape(value)[1], 2,
                                         message=f"{name} needs at least two classes")
        tf.debugging.assert_all_finite(value, f"{name} must be finite")
        tf.debugging.assert_greater_equal(value, 0., message=f"{name} must be one-hot")
        tf.debugging.assert_less_equal(value, 1., message=f"{name} must be one-hot")
        tf.debugging.assert_equal(value, tf.round(value), message=f"{name} must be one-hot")
        tf.debugging.assert_equal(tf.reduce_sum(value, axis=1),
                                  tf.ones(tf.shape(value)[0]), message=f"{name} must be one-hot")
        return value

    labels = validate_labels(labels, "labels")
    if targeted:
        if target_labels is None:
            raise ValueError("target_labels are required for a targeted attack")
        loss_labels = validate_labels(target_labels, "target_labels")
        tf.debugging.assert_equal(tf.shape(loss_labels), tf.shape(labels),
                                  message="target_labels must match labels shape")
    else:
        if target_labels is not None:
            raise ValueError("target_labels must be omitted for an untargeted attack")
        loss_labels = labels
    if from_logits is None:
        from_logits = infer_from_logits(model)

    loss_function = tf.keras.losses.CategoricalCrossentropy(
        from_logits=from_logits, reduction=tf.keras.losses.Reduction.NONE
    )
    with tf.GradientTape() as tape:
        tape.watch(images)
        predictions = tf.convert_to_tensor(model(images, training=False))
        tf.debugging.assert_rank(predictions, 2, message="predictions must be [N, C]")
        tf.debugging.assert_equal(tf.shape(predictions), tf.shape(labels),
                                  message="predictions must match labels shape")
        tf.debugging.assert_all_finite(predictions, "predictions must be finite")
        if not from_logits:
            tf.debugging.assert_greater_equal(
                predictions, tf.cast(0., predictions.dtype),
                message="probabilities must be in [0, 1]",
            )
            tf.debugging.assert_less_equal(
                predictions, tf.cast(1., predictions.dtype),
                message="probabilities must be in [0, 1]",
            )
            # Check in float64 so summation does not hide low-precision errors.
            # Tolerance accounts for probability quantization in the output dtype.
            tolerance = (1e-2 if predictions.dtype == tf.bfloat16 else
                         1e-3 if predictions.dtype == tf.float16 else 1e-5)
            tf.debugging.assert_near(
                tf.reduce_sum(tf.cast(predictions, tf.float64), axis=1),
                tf.ones(tf.shape(predictions)[0], dtype=tf.float64),
                atol=tolerance, rtol=0., message="probability rows must sum to one",
            )
        losses = loss_function(loss_labels, predictions)
        tf.debugging.assert_all_finite(losses, "losses must be finite")
        loss = tf.reduce_mean(losses)
        tf.debugging.assert_all_finite(loss, "mean loss must be finite")
    gradient = tape.gradient(loss, images)
    if gradient is None:
        raise RuntimeError("Could not compute the input gradient")
    tf.debugging.assert_all_finite(gradient, "input gradient must be finite")
    direction = -1.0 if targeted else 1.0
    adversarial = images + direction * float(epsilon) * tf.sign(gradient)
    return tf.clip_by_value(adversarial, 0.0, 1.0)
