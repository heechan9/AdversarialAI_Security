# Saved research diagnostics in MARIS

The new **Error analysis / 오류 분석** navigation item connects existing CLI diagnostics to the web. It supports classwise CNN error drilldown and investigation of the preserved external-run discrepancies. Original experimental results and the October 12 research panel are retained.

## Reviewed inputs

| PR | Reviewed head | Integrated behavior |
| --- | --- | --- |
| #106 | `bac3c909922e0e35fcce36acb82de15fdb1ac25a` | Audited, paired CNN predictions by condition and true class |
| #107 | `095d6f21a4e62556dfb302ddf5fa0a5ac27ba6d5` | Retests must identify the latest corrective action and source commit |
| #109 | `835868f5e097bccea0da97be2f1ad3b1eb761c19` | Saved discrepancy accounting with current status/lifecycle gates |
| #110 | `f8fd053f8879be1e9919b3aa03be1010a04fc39b` | Reject mathematically impossible paired clean/attack counts |

Integration base: `d4b092361c16fff875e1d13532dacf5230564216`.
The original source PRs remain separate; this candidate composes their reviewed changes and the web connection.

## Data flow and behavior

`python web/maris/scripts/export-research-diagnostics.py` runs the saved CNN auditor for all three conditions and calls discrepancy triage through the authoritative status/lifecycle gate. It generates `web/maris/public/evidence/research-diagnostics.json` deterministically. `--check` rejects missing or stale output and runs in CI.

The browser validates row/summary accounting before showing statistics. Class selection changes the metric cohort; paired-outcome selection changes only the case list. Model-specific own-clean ASR and B/C common-clean ASR retain separate denominators. Clean or zero-denominator ASR is displayed as undefined (`—`).

The external view selects method, model, evaluation path and exact image ID. Its full-condition totals remain fixed at 62,480 prediction cells, 16 differences and 14 unique affected images. Zero-result selections preserve the external verdict. Condition groups include zero-difference conditions.

CSV downloads include every selected case, across all pages, and retain headers when empty. JSON adds selection metadata, unfiltered cohort metrics or condition groups, evidence hashes, source metadata and study limitations. Filenames and predictions come only from already-public saved records. Images and model binaries are not copied.

## Verification

- 103 backend tests passed together: saved audit, class diagnostics, lifecycle, status and discrepancy triage.
- New frontend checks: 1,008 filter/export combinations, 406 Korean/English SSR renders and 8 rejected snapshot mutations.
- Existing evidence checks passed, including the #110 exhaustive oracle (494 feasible and 660 impossible count combinations, plus 2 class inconsistencies).
- Existing localization, interactions, mission and paired-review checks passed; TypeScript and production build passed. Lint has zero errors and the existing image-optimization warning.
- Managed Chrome preview: class/outcome changes, Container Ship six-case selection with denominator 86 and net -4, Tug empty selection with denominator 68, external CNN empty selection, preserved verdicts, and English switching were verified. Downloaded CSV/JSON bytes were checked. Physical mobile device and viewport-resize QA were not performed.

These are software and saved-evidence checks. No model inference, retraining or independent experimental reproduction was performed. External Stage B remains **FAIL**, the PC record remains **LOCAL_PASS**, cause remains **UNRESOLVED**, and the discrepancy remains **open**. Missing historical training manifests are not repaired by this integration. Existing license scope is unchanged.
