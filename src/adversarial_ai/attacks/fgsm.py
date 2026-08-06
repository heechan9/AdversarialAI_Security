"""One-step Fast Gradient Sign Method attacks for TensorFlow/Keras models."""

from __future__ import annotations

from typing import Any


def infer_from_logits(model: Any) -> bool:
    """Return the correct cross-entropy mode from the final activation."""
    import tensorflow as tf

    activation = getattr(model.layers[-1], "activation", None)
    if activation is None:
        raise ValueError("The final model layer does not expose an activation")
    name = tf.keras.activations.serialize(activation)
    if name == "softmax":
        return False
    if name == "linear":
        return True
    raise ValueError(f"Unsupported final activation for FGSM: {name!r}")


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
    labels use the same one-hot format as the ship classifiers.
    """
    import tensorflow as tf

    if epsilon < 0:
        raise ValueError("epsilon must be non-negative")
    images = tf.convert_to_tensor(images, dtype=tf.float32)
    labels = tf.convert_to_tensor(labels, dtype=tf.float32)
    if targeted:
        if target_labels is None:
            raise ValueError("target_labels are required for a targeted attack")
        loss_labels = tf.convert_to_tensor(target_labels, dtype=tf.float32)
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
        predictions = model(images, training=False)
        loss = tf.reduce_mean(loss_function(loss_labels, predictions))
    gradient = tape.gradient(loss, images)
    if gradient is None:
        raise RuntimeError("Could not compute the input gradient")
    direction = -1.0 if targeted else 1.0
    adversarial = images + direction * float(epsilon) * tf.sign(gradient)
    return tf.clip_by_value(adversarial, 0.0, 1.0)
