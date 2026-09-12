# Research + defense integration review

Review-only: not merged into main; no official result promotion.

## What is reconciled

PR #24 (`2b5256f`) research-readiness work and PR #25 (`af96a1f`) defense
code/evidence are combined in this Draft branch. The only merge conflict was
CONTRIBUTIONS.md; both original contribution sections were retained. Parent
history preserves the existing implementation authors. Original result files
and uploaded ZIP/member hashes are unchanged.

## Direct verification

- Linux Python 3.12 with TensorFlow 2.21.0/Keras 3.15.1: 239 passed,
  2 dependency deprecation warnings, 13.16 seconds.
- Research Evidence Audit: PASSED; raw local image/model content unavailable here.
- Paper Claim Audit: PASSED (9/9; existing ACK v1.5 snapshot).
- Independent Gaussian Evidence Audit: PASSED, 6248 rows, 8 conditions,
  80 class summaries. Standard-library-only; no evaluator/model execution.
- Independent Stage A clean artifact recomputation: PASS.
- No timestamp-only changes to committed research audit reports are included.

These checks do not establish general defense robustness or official adoption.
Windows full combined suite has not been executed; the user supplied 28 passing
Windows defense component tests and a completed experimental evaluation.

## Completed without another PC experiment

- Standalone archived-defense audit and hash-refreshed mutation tests.
- Research-readiness and defense branch conflict reconciliation.
- Paper defense supplement v2.5, with source-derived table and claim limits.
- Original experimental results preserved; no kernel tuning or rerun.

## Still requires external input or a separate decision

- Taehee/Jaehyuk image-review responses, including human versus AI confirmation.
- Giho's independent artifact review response; do not fabricate sign-off.
- Team decision on manuscript scope, author/affiliation details and data-use basis.
- Final ACK document/PDF layout and claim-snapshot update after scope decision;
  the supplement is not a replacement submission-ready PDF.
- User confirmation before main merge or official result promotion.
- MARIS defense imagery needs actual verified visual artifacts; aggregate CSV
  does not justify generating a defense image or heatmap. No site changes here.

No additional attack or defense execution is needed merely to wait for these
reviews. Stronger attacks or defense retraining remain separate experiments.
