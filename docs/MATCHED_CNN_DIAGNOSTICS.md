# Saved CNN error diagnostics

The October 24 matched-CNN panel shows overall scores. This tool traces those
scores to classwise counts and the exact saved cases where clean-only and
PGD-mixed models differ. It reuses the existing saved-evidence auditor before
producing any output; it performs no model inference or training.

## Run

Python 3.11+ standard library, from the repository root:

```bash
python verification/matched_cnn_diagnostics.py --condition pgd50 --output-dir /tmp/paulguard-pgd50-review
python verification/matched_cnn_diagnostics.py --condition pgd50 --class-name "Container Ship" --outcome newly_incorrect --output-dir /tmp/paulguard-container-losses
```

Use new output directories. Existing directories and research inputs are never
overwritten. A failed evidence audit stops the command before output creation.
Without `--output-dir`, the report is printed as JSON.

Outputs:

- `report.json`: overall and ten true-class summaries, selected-class metrics,
  model-specific ASR counts, B/C common-clean ASR, paired outcomes, source hashes,
  and the selected case records.
- `cases.csv`: selected original image paths, true class/index, each model's
  clean and selected-condition predictions, and the B/C paired outcome.

`--condition` accepts `clean`, `pgd7`, or `pgd50`. `--class-name` uses the exact
label in `configs/classes.json`. `--outcome` accepts `changed` (default), `all`,
`newly_correct`, `newly_incorrect`, `both_correct`, or `both_wrong`.

Class selection changes the metric population. Outcome selection changes only
the exported case list, never the accuracy/ASR denominators. For example, the
default PGD50 export has 49 changed cases, while its overall metrics still use
781 samples. Reports retain both the overall and selected-class summaries.

## Expected saved-record checks

For all classes under PGD50:

- PGD-mixed accuracy: 48/781; own-clean ASR: 492/540.
- Mixed versus clean-only: 28 newly correct, 21 newly incorrect, 20 both correct,
  712 both wrong; net +7 correct.
- B/C common-clean cohort: 518 original images; ASR successes B=477, C=470.
  This selected cohort is distinct from each model's own-clean denominator.
- True-class counts sum to 781, and their integer metric counts sum to the
  overall counts. Never average class ASR percentages without their denominators.

`clean` has no attack ASR. Zero denominators are `null`, not a zero success rate.
The common-clean cohort is not proof of independent samples or identical
perturbations: attacks were constructed separately using each model's gradient.
Paired outcomes match original image IDs, not a single shared adversarial image.

## Workflow supported by the feature

1. Select a recorded attack condition and inspect affected classes.
2. Export newly incorrect cases to trace a reported regression to saved predictions.
3. Compare gains and harms before writing a conclusion or choosing a next check.
4. Record any proposed cause as a hypothesis until a separate controlled test supports it.

This is diagnostic software, not a new performance improvement. It does not
estimate significance, bootstrap confidence intervals, or causal training
effects. Only one completed training seed is represented. External Stage B FAIL,
Hyunsu's selected diagnostic INCOMPLETE, unresolved baseline training exposure,
missing historical training manifests, data-rights uncertainty, and vessel/scene
independence limits remain unchanged. The original paper, evidence and team
attribution are not modified. No raw images or model weights are exported.

## Verification

```bash
python -m unittest discover -s tests -p 'test_matched_cnn_diagnostics.py' -v
python -m unittest discover -s tests -p 'test_matched_cnn_saved_audit.py' -v
```

Implementation and scoped software checks: Codex assistance following Heechan
Choi's request for functional analysis improvements. User execution, independent
model reproduction and Claude/Jules review are not implied.
