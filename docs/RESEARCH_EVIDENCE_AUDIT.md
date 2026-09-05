# Research Evidence Audit Documentation

## Overview
This document details the independent audit framework implemented for verifying research evidence in `AdversarialAI_Security` (GitHub Issue #2).

The audit verifies the clean baseline evaluations, provisional FGSM attack results, manifest records, model SHA-256 integrity, attack contract invariants, cross-document claims, and artifact provenance without modifying existing models, weights, preprocessing, or canonical results.

## CLI Usage

Run the independent audit CLI:

```bash
python scripts/audit_research_evidence.py
```

Or via module invocation:

```bash
python -m adversarial_ai.audit
```

Exit Codes:
- `0`: Audit PASSED successfully. Audit report written to `results/audit/evidence_audit_report.json`.
- `1`: Audit FAILED due to evidence tampering, schema errors, missing files, or contract violations.

## Audited Evidence Scopes

1. **Manifest Integrity (`configs/test_manifest.json`)**:
   - Validates `test_samples = 781`.
   - Validates `test_files` ordering, required fields (`relative_path`, `label`, `sha256`), and lowercase SHA-256 format.
   - Computes image file content SHA-256 digests if images are present on disk.

2. **Model Integrity**:
   - Cross-checks CNN (`cb256b1a...`) and MobileNetV2 (`58c4878f...`) SHA-256 hashes between `test_manifest.json`, evaluation metadata JSONs, and disk binaries (if present).

3. **Clean Baseline Results**:
   - Dynamically recalculates correct counts and accuracy from `results/clean/cnn_baseline_eval.csv` and `results/clean/mobilenet_eval.csv`.
   - Confirms CNN correct count is exactly **504 / 781** (Accuracy: 0.645326) and MobileNetV2 correct count is exactly **613 / 781** (Accuracy: 0.784891).

4. **Provisional FGSM Attack Results ($\varepsilon \in \{0, 0.01, 0.03, 0.05\}$)**:
   - Dynamically recalculates robust accuracy, accuracy drop, attack successes, and Untargeted ASR from provisional CSV sample files.
   - Verifies ASR denominators are derived exclusively from clean-correct samples (CNN denominator **504**, MobileNetV2 denominator **613**).
   - Verifies attack contract invariants: $[0,1]$ input/output bounds, $L_\infty \le \varepsilon + 1e-6$, and at $\varepsilon=0$: drop=0, ASR=0, attack successes=0, $L_\infty=0$.

5. **Cross-Document & Provenance Verification**:
   - Cross-verifies claims across `README.md`, `docs/EXPERIMENT_CONTRACT.md`, `docs/CLEAN_BASELINE_RESULTS.md`, `docs/FGSM_PROVISIONAL_RESULTS.md`, and `results/attacks/provisional/PROVENANCE.json`.
   - Confirms MobileNet preprocessing limitation disclosure is preserved.

6. **Strict Visual Review Evidence Audit**:
   - Dynamically derives candidate images where both CNN and MobileNetV2 predict the same misclassified class with unrounded confidence >= 0.70.
   - Validates split review files (`review_taehee_visual_strict_final.csv`, `review_jaehyuk_visual_strict_final.csv`) and combined file (`63_images_strict_visual_audit.csv`).
   - Verifies exact ordered Korean schema, required UTF-8 BOM, evidence-manifest SHA-256 values, ISO review dates, one consistent strict-review criterion, non-repeated unique visual notes, split disjointness, union equality, and record agreement with canonical Clean baseline evaluations.
   - Compares displayed confidence values with the canonical unrounded predicted-class confidence after the explicitly declared three-decimal rounding step; it does not use a broad tolerance. See `docs/VISUAL_REVIEW_AUDIT.md`.

## Verified vs. Unverified Scopes on Clean Checkout

When executed on a clean git checkout (where raw image dataset and `.h5` model binaries are intentionally omitted from git tracking per reproducibility policy):
- **Verified**: Manifest structure, CSV predictions, report metrics, contract bounds, metadata hashes, cross-document claims, provenance bundle SHA.
- **Unverified (Gracefully handled)**: Raw image content SHA-256 and `.h5` binary file hashes on disk. These are logged in `unverified_scopes` in the audit report artifact.

## Audit Artifact

Audit outputs are saved to `results/audit/evidence_audit_report.json` containing:
- `status`: `"PASSED"`
- `source_commit_sha`: Git commit SHA of the codebase state audited.
- `timestamp_utc`: ISO-8601 UTC timestamp.
- `verified_scopes`: List of checked evidence items.
- `unverified_scopes`: List of items omitted due to clean checkout environment.
- `summary`: Recalculated clean and FGSM metrics.
