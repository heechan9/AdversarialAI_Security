"""Claim-level audit for paper-facing Clean and provisional FGSM evidence."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from adversarial_ai.audit.clean import audit_clean_evaluation
from adversarial_ai.audit.cross_doc import audit_cross_documents
from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.fgsm import EXPECTED_EPSILONS, audit_fgsm_results
from adversarial_ai.audit.manifest_models import audit_manifest
from adversarial_ai.audit.visual_review import audit_visual_reviews


@dataclass(frozen=True)
class PaperClaim:
    claim_id: str
    metric_name: str
    status: str
    evidence: str
    actual: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _close(actual: Any, expected: float, *, tolerance: float = 1e-6) -> bool:
    try:
        return abs(float(actual) - float(expected)) <= tolerance
    except (TypeError, ValueError):
        return False


def _audit_comparison_summary(
    summary_path: Path,
    clean: dict[str, dict[str, Any]],
    fgsm: dict[str, dict[float, dict[str, Any]]],
) -> int:
    if not summary_path.is_file():
        raise AuditError(f"Paper-facing FGSM comparison summary is missing: {summary_path}")

    try:
        frame = pd.read_csv(summary_path)
    except Exception as exc:
        raise AuditError(
            f"Failed to read paper-facing FGSM comparison summary: {summary_path}",
            {"error": str(exc)},
        ) from exc

    required = {
        "status",
        "model",
        "epsilon",
        "n_samples",
        "clean_accuracy",
        "robust_accuracy",
        "accuracy_drop",
        "untargeted_asr",
        "attack_successes",
        "asr_denominator_clean_correct",
    }
    missing = required - set(frame.columns)
    if missing:
        raise AuditError(f"FGSM comparison summary missing columns: {sorted(missing)}")

    expected_keys = {
        (model, float(epsilon))
        for model in ("cnn", "mobilenet")
        for epsilon in EXPECTED_EPSILONS
    }
    actual_keys = list(zip(frame["model"].astype(str), frame["epsilon"].astype(float)))
    if len(actual_keys) != len(set(actual_keys)):
        raise AuditError("FGSM comparison summary contains duplicate model/epsilon rows")
    if set(actual_keys) != expected_keys:
        raise AuditError(
            "FGSM comparison summary model/epsilon set disagrees with canonical sweep",
            {"expected": sorted(expected_keys), "actual": sorted(actual_keys)},
        )

    for row in frame.to_dict(orient="records"):
        model = str(row["model"])
        epsilon = float(row["epsilon"])
        clean_result = clean[model]
        attack_result = fgsm[model][epsilon]

        if str(row["status"]).lower() != "provisional":
            raise AuditError(
                "FGSM comparison summary must remain provisional before mentor approval",
                {"model": model, "epsilon": epsilon, "status": row["status"]},
            )
        if int(row["n_samples"]) != int(clean_result["total_samples"]):
            raise AuditError("FGSM comparison summary sample count mismatch", row)
        if not _close(row["clean_accuracy"], clean_result["accuracy"]):
            raise AuditError("FGSM comparison summary clean accuracy mismatch", row)
        if not _close(row["robust_accuracy"], attack_result["robust_accuracy"]):
            raise AuditError("FGSM comparison summary robust accuracy mismatch", row)

        expected_drop = clean_result["accuracy"] - attack_result["robust_accuracy"]
        if not _close(row["accuracy_drop"], expected_drop):
            raise AuditError("FGSM comparison summary accuracy drop mismatch", row)
        if not _close(row["untargeted_asr"], attack_result["untargeted_asr"]):
            raise AuditError("FGSM comparison summary ASR mismatch", row)
        if int(row["attack_successes"]) != int(attack_result["attack_successes"]):
            raise AuditError("FGSM comparison summary attack-success count mismatch", row)
        if int(row["asr_denominator_clean_correct"]) != int(
            attack_result["asr_denominator"]
        ):
            raise AuditError("FGSM comparison summary ASR denominator mismatch", row)

    return len(frame)


def audit_paper_claims(repo_root: Path = Path(".")) -> list[PaperClaim]:
    """Derive paper-facing claims from canonical evidence rather than literals."""

    repo_root = repo_root.resolve()
    manifest = audit_manifest(repo_root / "configs" / "test_manifest.json")

    clean = {
        "cnn": audit_clean_evaluation(
            repo_root / "results" / "clean" / "cnn_baseline_eval.csv",
            summary_json_path=repo_root
            / "results"
            / "clean"
            / "cnn_baseline_summary.json",
        ),
        "mobilenet": audit_clean_evaluation(
            repo_root / "results" / "clean" / "mobilenet_eval.csv",
            summary_json_path=repo_root
            / "results"
            / "clean"
            / "mobilenet_summary.json",
        ),
    }

    provisional_dir = repo_root / "results" / "attacks" / "provisional"
    fgsm = {
        model: audit_fgsm_results(
            provisional_dir,
            model,
            clean_result["correct_count"],
            clean_result["clean_correct_mask"],
        )
        for model, clean_result in clean.items()
    }

    comparison_rows = _audit_comparison_summary(
        provisional_dir / "fgsm_comparison_summary.csv", clean, fgsm
    )
    cross_doc = audit_cross_documents(repo_root, clean, fgsm)

    evidence_dir = repo_root / "results" / "audit" / "evidence"
    visual = audit_visual_reviews(
        evidence_dir=evidence_dir,
        clean_cnn_csv=repo_root / "results" / "clean" / "cnn_baseline_eval.csv",
        clean_mobilenet_csv=repo_root / "results" / "clean" / "mobilenet_eval.csv",
    )

    zero_control = all(
        result[0.0]["attack_successes"] == 0
        and result[0.0]["untargeted_asr"] == 0.0
        and result[0.0]["max_linf"] == 0.0
        for result in fgsm.values()
    )
    if not zero_control:
        raise AuditError("Paper claim epsilon=0 control is not satisfied")

    linf_contract = all(
        metrics["max_linf"] <= epsilon + 1e-6
        for result in fgsm.values()
        for epsilon, metrics in result.items()
    )
    if not linf_contract:
        raise AuditError("Paper claim L_infinity contract is not satisfied")

    clean_actual = ", ".join(
        f"{model}={result['correct_count']}/{result['total_samples']} "
        f"({result['accuracy']:.6f})"
        for model, result in clean.items()
    )
    denominator_actual = ", ".join(
        f"{model}={result['correct_count']}" for model, result in clean.items()
    )

    return [
        PaperClaim(
            "CLAIM-001",
            "test_manifest_integrity",
            "passed",
            "configs/test_manifest.json",
            f"{manifest['test_samples']} ordered samples",
        ),
        PaperClaim(
            "CLAIM-002",
            "clean_baseline_metrics",
            "passed",
            "results/clean/*_eval.csv + *_summary.json",
            clean_actual,
        ),
        PaperClaim(
            "CLAIM-003",
            "fgsm_clean_correct_denominator",
            "passed",
            "clean prediction CSVs + provisional FGSM sample CSVs",
            denominator_actual,
        ),
        PaperClaim(
            "CLAIM-004",
            "epsilon_zero_control",
            "passed",
            "provisional FGSM sample CSVs",
            "drop=0, ASR=0, attack_successes=0, max_linf=0",
        ),
        PaperClaim(
            "CLAIM-005",
            "linf_bound",
            "passed",
            "provisional FGSM sample CSVs",
            "max_linf <= epsilon + 1e-6 for all model/epsilon rows",
        ),
        PaperClaim(
            "CLAIM-006",
            "paper_fgsm_summary_consistency",
            "passed",
            "results/attacks/provisional/fgsm_comparison_summary.csv",
            f"{comparison_rows} rows derived from canonical sample evidence",
        ),
        PaperClaim(
            "CLAIM-007",
            "cross_document_provenance",
            "passed",
            "README, experiment/result docs, and PROVENANCE.json",
            f"{len(cross_doc['checked_files'])} files checked",
        ),
        PaperClaim(
            "CLAIM-008",
            "strict_visual_review_evidence",
            "passed",
            "results/audit/evidence/*.csv + manifest.json",
            f"{visual['total_candidates']} candidate samples verified across Taehee ({visual['split_counts']['taehee']}) and Jaehyuk ({visual['split_counts']['jaehyuk']}) splits",
        ),
    ]
