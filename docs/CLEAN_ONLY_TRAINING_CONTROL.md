# Clean-only fine-tuning control (prepared, not experimentally run)

The existing original-versus-adversarially-fine-tuned CNN comparison changes both
the training exposure and the objective. It does not isolate the contribution of
the adversarial loss. A matched clean-only fine-tuning arm is a project-specific
application of REFORMS guideline 5f: report baseline training/optimization and
use the same model-selection methods for comparative baselines. REFORMS does not
prescribe this exact experiment: https://reforms.cs.princeton.edu/ and
https://arxiv.org/abs/2308.07832.

## Implementation boundary

- `--training-mode pgd_mixed` is the default and retains the existing 50:50
  clean/PGD loss and operation order. Canonical results are unchanged.
- `--training-mode clean_only` uses one clean training forward per batch and
  entirely skips attack generation and the adversarial training forward. Merely
  multiplying the adversarial loss by zero would still change BatchNorm state
  and consume random numbers. Clean-only training retains input/configuration
  validation before the forward, including one-hot labels and the built
  classifier's input/output shapes.
- Both modes retain the same validation PGD evaluation and select the earliest
  epoch with the highest validation PGD accuracy. "Clean-only" describes the
  training objective; it does not mean that validation is clean-only.
- Same initial model, split content, seed, ordering, optimizer, epochs, batch
  size, learning rate and validation settings are required for a matched pair.
  Seeds/configuration do not promise identical random-number trajectories:
  the mixed arm deliberately executes additional stochastic layers.
- Report and checkpoint identities include the training mode and shared
  comparison protocol. A checkpoint cannot resume under the other mode. Existing
  historical checkpoints are not silently upgraded into this new protocol.
- Resumed output leaves and the checkpoint root are checked for symlinks before
  writes; writable file leaves also reject hardlinks and nonregular file types.
  The checkpoint root must be a directory. These guards reject
  pre-existing redirected targets and do not promise safety against a concurrent
  process changing filesystem links between a check and a write.

## Future paired experiment

Create two new run IDs from the same committed source and verified split/model
inputs. Use identical settings in both invocations, changing only the run ID and
`--training-mode`. This preparation does not authorize or execute those runs.
Do not compare a new clean-only run to a historical mixed run as if their source,
settings, checkpoint selection and execution environment were matched.

The metadata hash omits run IDs and absolute input paths, because the split audit
and initial-model hashes identify the input contents. Source, model, split,
configuration, recorded numerical environment and Python/NumPy/TensorFlow/Keras
differences reject pairing. Run both arms in
the same recorded hardware/software environment; the audit cannot authenticate
execution or prove hardware identity from metadata.

After both runs finish, the standard-library-only saved-artifact audit is:

```bash
PYTHONPATH=src:. python verification/training_control_audit.py /private/clean-run /private/mixed-run
```

It verifies report consistency, full epoch coverage, validation selection, split
audit bytes and selected checkpoint bytes. It performs no model inference.
Then evaluate both frozen checkpoints under the same separately fixed stronger
white-box/black-box suite, report clean accuracy, attack-conditioned accuracy and
clean-correct ASR together, and preserve all seeds. Training completion or a
matching protocol is not evidence of a benefit.

The known near-duplicate/group-split gap and the original checkpoint's historical
data exposure remain. This control does not repair either limitation or replace
independent Stage B reproduction, PR #78's remaining experiments, or PR #86's
interrupted-FGSM work.
