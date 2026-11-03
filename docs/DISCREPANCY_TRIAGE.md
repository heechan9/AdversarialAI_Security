# Saved external discrepancy triage

An aggregate external FAIL does not tell a reviewer which condition, pipeline or original image ID to investigate. `verification/discrepancy_triage.py` turns existing hash-locked public label diagnostics into a deterministic JSON drilldown. It uses the existing status/lifecycle validator, then checks each difference against the manifest row, class map, condition count and correctness delta. No model, image or original CSV is opened or altered.

This applies evidence-first engineering: define an observable problem, inspect records, prepare a reproducible investigation and state the limits. It does not turn model accuracy into semiconductor yield, use SPC limits on repeated prediction cells, or equate correlation with cause.

## Usage

Python 3.10+ standard library is enough for the CLI. From a complete checkout with these new files:

```sh
python verification/discrepancy_triage.py
python verification/discrepancy_triage.py --method gaussian --pipeline transfer_defended
python verification/discrepancy_triage.py --relative-path 'Bulkers/Bulkers_1039.jpeg'
python verification/discrepancy_triage.py --model cnn
```

JSON goes to stdout; no output directory is created. Optional shell redirection follows normal shell overwrite behavior, so choose a fresh path yourself. Exit 0 means the saved report was valid and generated, **not** external verification PASS. Invalid evidence gives exit 2 and no JSON report.

Method/model/pipeline/exact image-ID filters combine to select case records only. Totals, all 80 condition groups and affected-image counts retain the full population. A nonexistent image ID gives an empty selection. The image ID is never opened as a filesystem path.

Each case includes method/model/epsilon/pipeline, row, original image ID, reference/actual/true labels, correctness outcome, evidence JSON path/hash, diagnostic source commit and recorded reference/actual CSV hashes. The latter are preserved declarations, not newly hashed private CSV bytes. Manifest and class-map hashes are emitted as well.

## Saved evidence at reviewed base

Upstream base: `2ed69b00faa3dce098a6a78888032746b6b35d43`.

- 62,480 compared prediction cells: two methods, two models, four epsilons and five pipelines. The same 781 image IDs recur across conditions.
- 16 differing cells, 14 distinct affected image IDs. Gaussian has 10, mean 6; all listed differences are MobileNet.
- `Bulkers/Bulkers_1039.jpeg` selects two attacked-condition records at epsilon 0.03, manifest row 99, reference 1 to actual 6, true class 1, one per method. These are two records of one image, not independent observations.
- CNN filter gives zero discrepancy cases while full denominators remain unchanged.
- PC remains LOCAL_PASS, external remains FAIL, discrepancy remains open, cause remains UNRESOLVED.

This is saved-record analysis, not inference, raw CSV re-audit, cause confirmation, severity, statistical significance or a general security guarantee. Original training manifests remain unrecovered. Submitted paper, historical results, models/data, contributions and deployment are unchanged.

## Verification and portfolio boundary

```sh
python -m pytest tests/test_discrepancy_triage.py tests/test_issue_lifecycle.py tests/test_verification_status.py -q
python verification/status_registry.py
python -O verification/discrepancy_triage.py --relative-path 'Bulkers/Bulkers_1039.jpeg'
```

The new tests cover saved totals, filtering, row traceability, read-only behavior, malformed and duplicate records, and no stdout report on corrupt evidence. Mutation inputs are explicitly synthetic test fixtures, never experiments. Existing CPU CI discovers the `tests/` directory; no workflow change is required.

A defensible portfolio description: Directed an evidence-traceable investigation tool for an unresolved cross-environment model discrepancy; Codex assisted implementation and focused software validation. Preserved FAIL and unresolved cause rather than treating report generation as successful reproduction.

Do not attribute independent implementation or test execution to the user without their own evidence. Existing team credit is unchanged. This demonstrates problem definition, data handling, reproducibility and technical reporting, not semiconductor process/device/equipment experience. No lecture assets are redistributed.
