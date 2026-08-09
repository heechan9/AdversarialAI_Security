"""Basic Iterative Method (BIM) adversarial attack for TensorFlow/Keras models.

Design notes (kept consistent with attacks/fgsm.py):
- Untargeted (default): each step moves in the direction that INCREASES the
  loss w.r.t. the true label (gradient ascent), same convention as
  ``generate_fgsm``.
- Targeted: each step moves in the direction that DECREASES the loss w.r.t.
  the target label (gradient descent toward the target), same convention as
  ``generate_fgsm``.
- No random start. The starting point is always the clean image
  (x_adv_0 = images). Random start is what distinguishes PGD from BIM in
  this codebase; it must not be introduced here, and there is no parameter
  that would allow a caller to enable it.
- Every step projects onto the L-infinity epsilon-ball around the ORIGINAL
  image and clips to the valid [0, 1] pixel range -- not only at the end.
- Reuses ``infer_from_logits`` from attacks/fgsm.py rather than duplicating
  the final-activation inspection logic.
"""

from __future__ import annotations

import math
from typing import Any

from adversarial_ai.attacks.fgsm import infer_from_logits


def _project(x: Any, x_orig: Any, epsilon: float) -> Any:
    """Project x onto the L-inf epsilon-ball around x_orig, then clip to [0, 1].

    This single helper is what every step (and the final result) goes
    through, so per-step ball-projection and pixel-clipping are the same
    code path -- there is no separate "final clip" that could silently
    diverge from the per-step behavior.
    """
    import tensorflow as tf

    delta = tf.clip_by_value(x - x_orig, -epsilon, epsilon)
    return tf.clip_by_value(x_orig + delta, 0.0, 1.0)


def _bim_single_step(
    model: Any,
    x_adv: Any,
    x_orig: Any,
    loss_labels: Any,
    loss_function: Any,
    epsilon: float,
    alpha: float,
    direction: float,
) -> Any:
    """One BIM iteration: gradient step + ball projection + pixel clip.

    The gradient is computed fresh from the CURRENT ``x_adv`` on every call
    (a new GradientTape watches whatever tensor is passed in), so each
    iteration steps from where the previous iteration actually landed --
    not from the original clean image and not from a stale gradient.
    """
    import tensorflow as tf

    with tf.GradientTape() as tape:
        tape.watch(x_adv)
        predictions = model(x_adv, training=False)
        loss = tf.reduce_mean(loss_function(loss_labels, predictions))
    gradient = tape.gradient(loss, x_adv)
    if gradient is None:
        raise RuntimeError("Could not compute the input gradient")
    tf.debugging.assert_all_finite(gradient, "BIM gradient contains NaN or Inf")
    x_new = x_adv + direction * alpha * tf.sign(gradient)
    return _project(x_new, x_orig, epsilon)


def generate_bim(
    model: Any,
    images: Any,
    labels: Any,
    epsilon: float,
    alpha: float,
    steps: int,
    *,
    targeted: bool = False,
    target_labels: Any | None = None,
    from_logits: bool | None = None,
) -> Any:
    """Run BIM for ``steps`` iterations and return adversarial images.

    Parameters mirror ``generate_fgsm`` where they overlap (``images``,
    ``labels``, ``epsilon``, ``targeted``, ``target_labels``,
    ``from_logits``), plus ``alpha`` (per-step size) and ``steps``
    (iteration count), which FGSM does not need since it is exactly one
    step.

    ``x_orig`` (the epsilon-ball reference point) is fixed to the clean
    ``images`` for the entire loop -- it is never updated to the running
    adversarial image, only ``x_adv`` is.
    """
    import tensorflow as tf

    if isinstance(epsilon, bool):
        raise ValueError("epsilon must not be a bool")
    if isinstance(alpha, bool):
        raise ValueError("alpha must not be a bool")
    if not math.isfinite(epsilon):
        raise ValueError("epsilon must be finite")
    if not math.isfinite(alpha):
        raise ValueError("alpha must be finite")
    if epsilon < 0:
        raise ValueError("epsilon must be non-negative")
    if alpha < 0:
        raise ValueError("alpha must be non-negative")
    if epsilon > 0 and alpha == 0:
        raise ValueError("alpha must be positive when epsilon is positive")
    if type(steps) is not int or steps <= 0:
        raise ValueError("steps must be a positive integer")

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
    direction = -1.0 if targeted else 1.0

    x_orig = images  # fixed epsilon-ball reference for the whole loop
    x_adv = tf.identity(images)  # no random start
    for _ in range(steps):
        x_adv = _bim_single_step(
            model, x_adv, x_orig, loss_labels, loss_function, epsilon, alpha, direction
        )
        tf.debugging.assert_all_finite(x_adv, "BIM output contains NaN or Inf")
        x_adv = tf.stop_gradient(x_adv)

    predictions = model(x_adv, training=False)
    tf.debugging.assert_all_finite(predictions, "BIM predictions contain NaN or Inf")

    return x_adv
