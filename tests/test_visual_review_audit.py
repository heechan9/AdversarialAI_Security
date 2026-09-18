"""Unit tests for strict visual review evidence audit module."""

from pathlib import Path

import pytest

from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.visual_review import audit_visual_reviews


def test_visual_review_audit_success() -> None:
    """Test that authoritative evidence passes strict visual review audit dynamically."""
    repo_root = Path(".")
    evidence_dir = repo_root / "results" / "audit" / "evidence"
    cnn_csv = repo_root / "results" / "clean" / "cnn_baseline_eval.csv"
    mob_csv = repo_root / "results" / "clean" / "mobilenet_eval.csv"

    res = audit_visual_reviews(
        evidence_dir=evidence_dir,
        clean_cnn_csv=cnn_csv,
        clean_mobilenet_csv=mob_csv,
        confidence_threshold=0.70,
    )

    assert res["status"] == "PASSED"
    assert res["total_candidates"] == res["split_counts"]["taehee"] + res["split_counts"]["jaehyuk"]
    assert sum(res["judgment_counts"].values()) == res["total_candidates"]
    assert "라벨 정확" in res["judgment_counts"]
    assert "라벨 오류 의심" in res["judgment_counts"]
    assert "판단 보류" in res["judgment_counts"]
    assert len(res["evidence_sha256"]) == 3
    assert res["candidate_rule"]["confidence_rounding_decimals"] == 3
    assert len(res["special_case_rows"]) == (
        res["judgment_counts"]["라벨 오류 의심"]
        + res["judgment_counts"]["판단 보류"]
    )
