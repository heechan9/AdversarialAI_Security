# Aggregate ASR input contract

`compute_untargeted_asr(y_true, clean_pred, adversarial_pred)` returns a tuple
`(float_rate, integer_successes, integer_clean_correct_denominator)`.

All three inputs must be nonempty one-dimensional sequences of nonnegative
integer class indices with identical shapes. Python lists/tuples and signed or
unsigned NumPy integer vectors are accepted. Floating labels (including 0.0),
booleans, strings, objects, negatives, scalars, matrices and broadcasting shapes
are rejected. NumPy masked arrays are rejected before conversion, including
arrays with no active mask, so hidden labels can never silently enter the
denominator. Callers must explicitly resolve missing samples before evaluation.
Without a class map this helper cannot validate an upper class
index; the evaluator remains responsible for its model/class-map contract.

A rate is defined only if at least one image is clean-correct. If none are,
the function raises `ValueError: ASR is undefined: no clean-correct samples`.
A measured 0.0 rate remains valid when the denominator is positive and no attack
succeeds. This avoids conflating an undefined experiment with a zero-success
attack, while keeping the existing float tuple contract for successful calls.
The separate classwise helper continues to use nullable rates for individual
classes with no clean-correct samples; its behavior is unchanged.

The FGSM evaluator propagates a descriptive error naming the model and epsilon
before writing a per-condition summary/report or final completion metadata for
that invalid condition. Previously completed conditions and any already-written
sample images are not rolled back. Do not treat leftover files after an error
as a completed run.

No saved CSV, paper metric, archived source contract, model weight or MARIS
snapshot is modified. Eight saved CNN/MobileNet epsilon cells are recomputed
exactly by regression tests, retaining the original 504/613 denominators.
MARIS continues to cite the source commit associated with its existing snapshot.

Validation commands (with requirements-ci.txt installed):

```bash
PYTHONPATH=src:. python -m pytest tests/test_asr_validation.py -q
PYTHONPATH=src:. python verification/ci_cpu.py
```

These check software behavior and public saved evidence, not private image
inference, GPU experiments or independent human approval.
