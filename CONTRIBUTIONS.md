# Project Contributions & Provenance

## Issue #2 / PR #3: Research Evidence Audit Framework

- **Issue**: [#2 - feat(audit): independently verify Clean and provisional FGSM evidence](https://github.com/heechan9/AdversarialAI_Security/issues/2)
- **Pull Request**: [#3 - feat(audit): independently verify Clean and provisional FGSM evidence](https://github.com/heechan9/AdversarialAI_Security/pull/3)
- **Merge Commit**: `455ae36946fcc0461148b1ced501718aa5f5c321`

### Contribution Breakdown

- **google-labs-jules[bot]**:
  - Implemented the independent research evidence audit framework package (`src/adversarial_ai/audit/`).
  - Added CLI tool (`scripts/audit_research_evidence.py`) and module entrypoint (`python -m adversarial_ai.audit`).
  - Generated audit report artifact (`results/audit/evidence_audit_report.json`).
  - Authored documentation (`docs/RESEARCH_EVIDENCE_AUDIT.md`).
  - Added unit test suite (`tests/test_audit.py`) and mutation test suite (`tests/test_audit_mutations.py`) proving tampered evidence causes non-zero exit codes.

- **heechan9**:
  - Defined audit scope and specifications in Issue #2.
  - Performed local environment validation on Windows using the full raw 781-image dataset and local `.h5` model binaries.
  - Verified cross-platform UTF-8 encoding compliance and test results.
  - Reviewed execution artifacts and approved integration into `main`.

## PR #11: Claim-Level Paper Evidence Audit

- **Pull Request**: [#11 - feat(audit): add claim-level paper evidence verification](https://github.com/heechan9/AdversarialAI_Security/pull/11)

### Contribution Breakdown

- **Codex**:
  - Designed and implemented the claim-level paper evidence audit module and CLI.
  - Added dynamic comparison of paper-facing FGSM summary rows against canonical Clean and sample-level FGSM evidence.
  - Added mutation tests for numeric tampering and premature `official` status changes.
  - Authored the Claim audit contract documentation.

- **heechan9**:
  - Selected the integration scope and preserved the provisional/official decision boundary.
  - Ran Windows validation with the full 781-image dataset and both local `.h5` model binaries.
  - Confirmed `47 passed, 2 skipped`, research evidence audit PASS, and paper Claim audit 7/7 PASS.
