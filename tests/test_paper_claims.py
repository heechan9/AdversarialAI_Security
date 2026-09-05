"""Tests for the claim-level paper evidence audit."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest

from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.paper_claims import audit_paper_claims


def _copy_evidence(tmp_path: Path) -> Path:
    repo_copy = tmp_path / "repo"
    repo_copy.mkdir()
    for item in ("configs", "docs", "results"):
        shutil.copytree(Path(item), repo_copy / item)
    shutil.copy2(Path("README.md"), repo_copy / "README.md")
    return repo_copy


def test_paper_claim_audit_derives_all_claims_from_canonical_evidence() -> None:
    claims = audit_paper_claims(Path("."))
    claim_ids = [claim.claim_id for claim in claims]

    assert claim_ids == [f"CLAIM-{number:03d}" for number in range(1, 9)]
    assert all(claim.status == "passed" for claim in claims)
    assert "504/781" in claims[1].actual
    assert "613/781" in claims[1].actual


def test_paper_claim_audit_rejects_tampered_comparison_summary(
    tmp_path: Path,
) -> None:
    repo_copy = _copy_evidence(tmp_path)
    summary_path = (
        repo_copy
        / "results"
        / "attacks"
        / "provisional"
        / "fgsm_comparison_summary.csv"
    )
    frame = pd.read_csv(summary_path)
    frame.loc[
        (frame["model"] == "cnn") & (frame["epsilon"] == 0.01),
        "robust_accuracy",
    ] = 0.999999
    frame.to_csv(summary_path, index=False)

    with pytest.raises(AuditError, match="robust accuracy mismatch"):
        audit_paper_claims(repo_copy)


def test_paper_claim_audit_rejects_official_label_before_approval(
    tmp_path: Path,
) -> None:
    repo_copy = _copy_evidence(tmp_path)
    summary_path = (
        repo_copy
        / "results"
        / "attacks"
        / "provisional"
        / "fgsm_comparison_summary.csv"
    )
    frame = pd.read_csv(summary_path)
    frame.loc[0, "status"] = "official"
    frame.to_csv(summary_path, index=False)

    with pytest.raises(AuditError, match="must remain provisional"):
        audit_paper_claims(repo_copy)
