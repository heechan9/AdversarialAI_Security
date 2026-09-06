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

## PR #17: Strict Visual-Review Audit Extension

- **Pull Request**: [#17 - feat(audit): implement strict visual-review evidence audit extension](https://github.com/heechan9/AdversarialAI_Security/pull/17)

### Contribution Breakdown

- **Google Jules**:
  - Implemented the strict visual-review evidence audit extension (`src/adversarial_ai/audit/visual_review.py`).
  - Integrated visual-review verification into the audit runner (`runner.py`) and paper claim audit (`paper_claims.py`, `CLAIM-008`).
  - Added unit tests (`tests/test_visual_review_audit.py`) and mutation tests (`tests/test_audit_mutations.py`).
  - Authored visual review audit documentation (`docs/VISUAL_REVIEW_AUDIT.md`).

- **Codex**:
  - Independently reviewed PR #17 and reproduced audit-bypass cases involving BOM removal, review dates, schema drift, strict-criterion changes, and overly broad confidence tolerance.
  - Hardened the audit with exact schema/BOM/date validation, canonical three-decimal confidence comparison, evidence SHA-256 verification, and expanded mutation tests.
  - Preserved the supplied CSV bytes through an explicit Git text-normalization rule and removed unsupported fixed test-count reporting.

- **김태희**:
  - Performed assigned partitioned visual review for 31 candidate images (`review_taehee_visual_strict_final.csv`).

- **이재혁**:
  - Performed assigned partitioned visual review for 32 candidate images (`review_jaehyuk_visual_strict_final.csv`).

- **최희찬 (heechan9)**:
  - Defined the audit extension scope and supplied the authoritative evidence CSV artifacts.
  - Authorized conservative code review and repository integration after all automated checks pass.

## Codex Security Audit

- **Codex**:
  - Independently reviewed the evidence-audit implementation for path handling,
    malformed CSV/JSON input, unsafe execution and deserialization, secret
    exposure, dependency and GitHub Actions risk, audit bypasses, and fail-open
    behavior.
  - Implemented fail-closed path, boolean, numeric, provenance, Git identity,
    canonical FGSM-row, classification-report, confusion-matrix, and summary
    validation.
  - Added mutation tests for the reproduced bypass cases and documented the
    remaining supply-chain and environment limitations.

- **최희찬 (heechan9)**:
  - Authorized the independent security-audit scope and requested review through
    a separate Draft pull request before integration.
