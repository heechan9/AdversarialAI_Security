# Continuation guards and verification limits

Continuation inherits audited whole conditions; it is not an independent model rerun.

The guards now reject changes to the evaluation runner as well as its inference dependencies. The runner contains random-seed, filter and model-call logic, so it cannot be treated as bookkeeping-only. This is a conservative whole-file comparison.

The standalone CSV auditor also compares parent execution/input identity and six protocol settings (`attack`, `steps`, `step_size`, `restarts`, `seed`, `batch_size`). Per-run bookkeeping such as `run_id`, `resume_from` and `data_dir` may differ. Independent verification approval remains false.

Existing output CSVs and `parent-run.json` must not be overwritten. A preflight check and exclusive creation protect existing files, including dangling symlinks.

## Important limitation: no whole-directory transaction

If another writer creates a destination after preflight, exclusive creation fails without replacing that file. CSVs created earlier by this attempt can remain. The report is not marked as inherited on this failure. Do not automatically retry into that directory or treat partial files as a completed run; inspect the failure and use a fresh output directory. This change does not claim atomic rollback.

The interpretation of a parent `ERROR` execution status with valid inherited whole-condition outputs is unchanged. `FULL_OUTPUTS_CONSISTENT` is a CSV consistency result, not independent execution approval or a claim that the parent run completed successfully.

## Synthetic checks

Run `python verification/continuation_regression_check.py`, or run the pytest wrapper `tests/test_continuation_regression_check.py`. The script checks source changes using a temporary Git repository, recalculates synthetic 781-row CSVs through the actual auditor, tests allowed bookkeeping changes and disallowed metadata/protocol changes, and exercises existing-file and concurrent-writer cases. It does not load models, execute attacks, verify current runtime image bytes, or claim GPU/environment equivalence.
