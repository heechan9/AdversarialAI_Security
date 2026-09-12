"""Audit the values transcribed into a specific paper draft against canonical evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


from adversarial_ai.audit.exceptions import AuditError


def _require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise AuditError(
            f"Paper snapshot mismatch: {label}",
            {"paper": actual, "canonical": expected},
        )


def _load_snapshot(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"Invalid paper claim snapshot: {path}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise AuditError("Paper claim snapshot must use schema_version 1")
    if data.get("document_status") != "draft":
        raise AuditError("ACK paper v1.5 snapshot must remain a draft")
    if set(data) != {"schema_version", "document_id", "document_status", "claims"}:
        raise AuditError("Paper claim snapshot top-level schema mismatch")
    return data


def audit_paper_snapshot(
    repo_root: Path,
    clean: dict[str, dict[str, Any]],
    fgsm: dict[str, dict[float, dict[str, Any]]],
    visual: dict[str, Any],
) -> dict[str, Any]:
    """Compare paper-displayed values with values dynamically derived from evidence."""

    path = repo_root / "configs" / "paper_claims" / "ack2026_v1_5.json"
    data = _load_snapshot(path)
    claims = data.get("claims")
    if not isinstance(claims, dict):
        raise AuditError("Paper claim snapshot claims must be an object")

    _require_equal(claims.get("test_samples"), len(clean["cnn"]["relative_paths"]), "test samples")
    for model in ("cnn", "mobilenet"):
        paper = claims["clean"][model]
        result = clean[model]
        _require_equal(paper["correct"], result["correct_count"], f"{model} clean correct")
        _require_equal(paper["total"], result["total_samples"], f"{model} clean total")
        _require_equal(
            paper["accuracy_6dp"], round(result["accuracy"], 6), f"{model} clean accuracy"
        )

    expected_fgsm_keys = {
        (model, epsilon)
        for model in ("cnn", "mobilenet")
        for epsilon in (0.01, 0.03, 0.05)
    }
    seen: set[tuple[str, float]] = set()
    for paper in claims.get("fgsm", []):
        model, epsilon = str(paper["model"]), float(paper["epsilon"])
        key = (model, epsilon)
        if key in seen:
            raise AuditError(f"Duplicate paper FGSM row: {key}")
        seen.add(key)
        result = fgsm[model][epsilon]
        expected = {
            "robust_accuracy_percent_2dp": round(result["robust_accuracy"] * 100, 2),
            "accuracy_drop_percent_2dp": round(
                (clean[model]["accuracy"] - result["robust_accuracy"]) * 100, 2
            ),
            "asr_percent_2dp": round(result["untargeted_asr"] * 100, 2),
            "successes": result["attack_successes"],
            "denominator": result["asr_denominator"],
        }
        for field, value in expected.items():
            _require_equal(paper.get(field), value, f"{model} eps={epsilon:g} {field}")
    _require_equal(seen, expected_fgsm_keys, "aggregate FGSM row set")

    classwise_rows = claims.get("classwise_fgsm", [])
    expected_classwise_keys = {
        (model, class_name)
        for model in ("cnn", "mobilenet")
        for class_name in ("DDG", "Sailboat")
    }
    classwise_keys: set[tuple[str, str]] = set()
    for paper in classwise_rows:
        model, epsilon, class_name = (
            str(paper["model"]),
            float(paper["epsilon"]),
            str(paper["class"]),
        )
        key = (model, class_name)
        if key in classwise_keys or epsilon != 0.03:
            raise AuditError(f"Unexpected or duplicate paper classwise FGSM row: {paper}")
        classwise_keys.add(key)
        # Reuse the classwise values already verified from canonical samples.
        class_result = fgsm[model][epsilon]["class_asr"][class_name]
        _require_equal(paper["denominator"], class_result["clean_correct_denominator"],
                       f"{model} {class_name} denominator")
        _require_equal(paper["successes"], class_result["attack_successes"],
                       f"{model} {class_name} successes")
    _require_equal(classwise_keys, expected_classwise_keys, "classwise FGSM row set")

    paper_visual = claims["visual_review"]
    _require_equal(paper_visual["total"], visual["total_candidates"], "visual total")
    _require_equal(
        paper_visual["split_counts"], visual["reviewer_counts"], "visual split counts"
    )
    _require_equal(
        paper_visual["judgment_counts"], visual["judgment_counts"],
        "visual judgment counts",
    )

    required_boundaries = {
        "fgsm_status": "provisional",
        "mass_or_cyber_physical_validation_claimed": False,
        "visual_review_used_as_model_performance_evidence": False,
        "review_design": "disjoint_split_not_double_review",
    }
    _require_equal(claims.get("boundaries"), required_boundaries, "claim boundaries")
    return {
        "document_id": data.get("document_id"),
        "fgsm_rows": len(seen),
        "classwise_rows": len(classwise_rows),
    }
