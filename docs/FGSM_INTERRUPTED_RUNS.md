# FGSM interruption, completeness, and safe restart

This workflow preserves the completed output files of a stopped run. It does not
promote research results, approve Stage B, or replace the historical September
2026 PC rerun record. Different run dates and configurations remain distinct.

## Audit before restarting

The audit is standard-library-only; it does not load TensorFlow or private
images/models. Run it against a stopped output folder and the matching source
checkout:

```bat
python verification/fgsm_run_audit.py C:\path\to\outputs --models mobilenet
```

It checks the exact 781 manifest paths and order, ten-class labels, prediction
indices, clean-correct/attack-success flags, epsilon, finite perturbation bounds,
epsilon-zero equality, cross-condition clean predictions, and present aggregate
metrics. New journals additionally check input identity and artifact hashes.

- A partial result exits with code **2**, and lists exactly which requested
  conditions are missing. `--allow-partial` explicitly permits exit 0 for planning;
  the JSON still says `PARTIAL_SAVED_SAMPLE_COVERAGE`.
- A malformed, truncated, duplicated, inconsistent, or altered condition fails.
  Preserve it for investigation. Do not edit it into a passing result.
- `FULL_REQUESTED_SAVED_SAMPLE_COVERAGE` describes saved-row coverage only.
  The audit performs no inference and does not authenticate historical execution.
- A legacy partial folder can have complete individual CSVs without final
  aggregate/metadata files. Its execution provenance remains unverified by this
  journal mechanism. Other established historical evidence is not invalidated.
- `completion_record_consistent` checks a new invocation's own completion record
  against its artifacts; it is not independent approval or proof of execution.
- `RUNNING` in a saved journal is not a process-liveness check. A hard termination
  can leave this status stale. Check the real process separately before restarting.

The sample CSVs serialize float32 perturbations, while original summaries use
pre-serialization float32 reductions. Recalculated `linf_max`/`linf_mean` therefore
use the existing saved-evidence audit’s `5e-10` serialization/reduction allowance.
Other summary metrics use `1e-12`;
the existing epsilon budget check remains `epsilon + 1e-6`. No frozen result,
scientific comparison tolerance, or independent approval criterion is changed.

## Run only the missing conditions into a new folder

If the actual audit finds only MobileNet epsilon 0.05 missing:

```bat
python -m adversarial_ai.evaluation.evaluate_fgsm_mobilenet --epsilons 0.05 --output C:\path\to\resume_mobilenet_eps005
```

Use the same verified model/data, source, environment, and numerical settings.
Do not restart a broader orchestration script or append into the old folder.
A fresh output directory is mandatory for another invocation of the same model.
Existing CNN and MobileNet outputs may share a directory, but another run for the
same model is rejected before loading a model or replacing any output.

You may inspect the old and new folders together:

```bat
python verification/fgsm_run_audit.py C:\path\to\outputs C:\path\to\resume_mobilenet_eps005 --models mobilenet
```

Each remains a separate invocation with separate provenance. The audit rejects
ambiguous duplicate conditions. It does not merge files, synthesize an overall
execution report, infer identical environments from matching predictions, or
upgrade legacy partial outputs into a new completed run.

## New evaluator journals

`fgsm_<model>_execution.json` is reserved exclusively before the invocation and
updated atomically. It records:

- Requested model, epsilons, input size, batch size, sample limit, and run ID
- Source commit/dirty status when available and hashes of inference dependencies
- Model, manifest and class-map hashes; Python/TensorFlow/Keras/NumPy and numerical
  environment settings
- Completed whole-condition summaries and artifact hashes
- `PREPARING`, `RUNNING`, `INTERRUPTED`, `ERROR`, or `COMPLETED_REQUESTED_SCOPE`

Catchable interruption records `INTERRUPTED` and preserves completed conditions.
Errors record `ERROR`; the original exception still propagates. Hard termination
can prevent a final update, so the audit validates saved files rather than
trusting a status string. The model weights and input integrity are checked again
before completion. A run requested with only epsilon 0.05 cannot stand for the
four-epsilon grid, the other model, Gaussian, Mean, or independent verification.

Restart is deliberately at whole-condition granularity. Partial batches are not
resumed, and no automatic cross-run adoption or in-place resume is supported.
