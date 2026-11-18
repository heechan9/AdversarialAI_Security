# Saved baseline-label diagnostic (not an approval gate)

This optional diagnostic reads an inert saved run, snapshots report/CSV/config bytes and uses an exact-pinned auditor before comparing clean labels. It performs no inference and writes no input files. `settings.resume_from: null` is the known runner's fresh-run default; continuation markers are otherwise excluded. Call `baseline_diagnostic.diagnose(run_dir, provenance)` with caller-attested report, execution, environment and settings identities. Attestation is not independent environment verification.

This revision requires the exact PR119 auditor SHA256 `c7f906a7f47c8671cebe5252f6e9b593a6a714b1bb3d68ecc56c866e313b6ed0`; old-main or modified auditor bytes fail before execution. Do not blindly update the pin. The diagnostic excludes continuation before audit, while the auditor's own continuation/lineage protection remains unchanged.

Clean labels group by model/hash; defended-clean also groups by filter. Comparisons use a sorted reference, not all pairs. Identical CSV content collapses conservatively, not as proof of actual reuse. Fewer than two distinct contents is NOT_COMPARABLE. MATCHED_OBSERVED_BASELINE_LABELS compares only supplied labels, not probabilities, images, actual model identity or correctness. MISMATCH does not establish cause. Approval stays false.

The source directory must be inert/trusted. This is not a transaction against hostile concurrent ancestor replacement or protection from a malicious Python environment. Caller input/provenance schema is intentionally narrow. Existing continuation per-file no-clobber is not whole-directory rollback.

## Synthetic verification

Run `PYTHONPATH=src:. python -m pytest tests/test_baseline_diagnostic_package.py -q` from repository root. Four wrapper tests generate fake 781-item identifiers/configs exclusively under a temporary directory and exercise 82 boundary cases, the original 17 checks, follow-up 18 cases and optimized continuation 33 checks. Counts overlap: do not sum them. No repository image manifest is copied; no real image, model, prediction or private record is accessed. Frozen code-only fixtures preserve the V2 comparison baseline and prior main auditor; fake configs are generated for both.

The integration was AI-assisted (Codex implementation/local synthetic verification and Claude source-only reviews, with a separate internal review). These are software checks, not independent model reproduction or experimental approval. Stage B FAIL/UNRESOLVED and existing evidence remain unchanged. No deployment is part of this change.
