# Opt-in validated FGSM API

For **new eager-execution experiments**, import the stricter entry point explicitly:

```python
from adversarial_ai.attacks.validated_fgsm import generate_fgsm

adversarial = generate_fgsm(model, images, one_hot_labels, epsilon=0.03)
# Targeted mode minimizes the loss for the supplied target class.
targeted = generate_fgsm(
    model, images, one_hot_labels, epsilon=0.03,
    targeted=True, target_labels=one_hot_targets,
)
```

`images` must be finite, nonempty NHWC tensors in [0, 1]. True labels and, if
used, target labels must be one-hot [N, C] with C >= 2 and matching batch/class
sizes. Finite Python/NumPy real scalar epsilon in [0, 1] is accepted, including
zero. NumPy scalar objects such as np.float32(.03) are accepted; zero-dimensional
arrays and TensorFlow scalar tensors are not. Boolean, nonfinite, negative, and
greater-than-one epsilon is rejected.
`targeted` and explicit `from_logits` must be Python booleans. For raw Keras
models the softmax/linear final activation determines the loss mode; defense
wrappers require `from_logits` explicitly, just as in the canonical API.

Malformed settings fail before model execution. Tensor contracts fail through
TensorFlow assertions; missing gradients raise RuntimeError. Nonfinite model
predictions, per-sample/mean loss, and input gradients are rejected. Epsilon=0
still validates the model and gradient, preserving the existing contract.
With `from_logits=False`, outputs must be probabilities in [0, 1], with each
row summing to one. Row sums are checked in float64 using absolute tolerance
1e-5 for float32/float64, 1e-3 for float16, and 1e-2 for bfloat16 (zero relative
tolerance), accounting for output quantization. Finite logits are unrestricted
when `from_logits=True`; negative or unnormalized logits are valid in that mode.

Finite zero gradients are allowed: the result is the unchanged input. This is
canonical FGSM behavior and is not proof that a model is robust or the attack
succeeded. Missing gradients and nonfinite gradients still fail explicitly.
Prediction ties are allowed. 1x1 images are supported by the raw FGSM API;
defense wrappers retain their own size requirements.

## Execution-mode safety boundary

Call this API eagerly, outside `tf.function` and XLA compilation. Both ordinary
outer graph tracing and `jit_compile=True` are rejected at entry with a clear
ValueError, before model execution. XLA can discard TensorFlow runtime assertion
ops; accepting graph mode would falsely promise fail-closed validation. This
explicit restriction uses the public `tf.executing_eagerly()` check rather than
private compiler detection or a Python callback barrier.

A model's **forward function** may itself be `tf.function`/XLA-compiled when this
attack API is called eagerly: input checks run before the model and prediction,
loss and gradient checks execute outside the compiled region. Regression tests
cover valid compiled forwards and nonfinite gradients returned by them. The
attack function itself is not a graph-export/SavedModel serving entry point.

## Historical-source boundary

The existing `adversarial_ai.attacks.fgsm` file is hash-locked by historical
Gaussian/Mean evidence archives. It remains byte-for-byte unchanged. Existing
FGSM runners, notebooks, and saved results still use that canonical module;
**they are not automatically upgraded or globally hardened by this addition**.
To use validation in a new experiment, change that experiment's import to the
new module and record its source identity. Do not update old evidence hashes
or represent a new run as reproducing the frozen historical source.

This is the same one-step FGSM algorithm with additional validation, not a new
attack or a change to accepted results. The stricter implementation is separate
so historical hashes remain valid. Regression tests compare exact adversarial
outputs against the canonical implementation for logits/softmax models, raw,
Gaussian and Mean wrappers, targeted/untargeted modes, and epsilon
0/.01/.03/.05/1; weights must remain unchanged.

## Validation

Use the pinned CPU environment in `requirements-ci.txt` and the established
workflow in [CPU_CI_REVIEW.md](CPU_CI_REVIEW.md):

```bash
PYTHONPATH=src:. python -m pytest tests/test_fgsm_validation.py -q
PYTHONPATH=src:. python verification/ci_cpu.py
```

These are synthetic CPU software tests and saved-evidence checks. They do not
rerun private 781-image inference, GPU experiments, or grant independent human
verification approval. No paper metrics, model weights, or saved artifacts are
changed.
