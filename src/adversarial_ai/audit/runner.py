"""Audit orchestrator runner for executing all research evidence checks."""

from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path
from typing import Any

from adversarial_ai.audit.clean import audit_clean_evaluation
from adversarial_ai.audit.cross_doc import audit_cross_documents
from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.fgsm import audit_fgsm_results
from adversarial_ai.audit.manifest_models import audit_manifest, audit_models
from adversarial_ai.audit.visual_review import audit_visual_reviews


def get_git_commit_sha(repo_root: Path = Path(".")) -> str:
    """Return current git HEAD commit SHA."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def run_full_audit(
    repo_root: Path = Path("."),
    manifest_path: Path | None = None,
    output_report_path: Path | None = None,
) -> dict[str, Any]:
    """Orchestrate all research evidence audit checks and output audit report artifact.

    Raises AuditError if any verification check fails.
    Returns structured audit report dict on success.
    """
    repo_root = repo_root.resolve()
    manifest_p = manifest_path or (repo_root / "configs" / "test_manifest.json")
    data_dir = repo_root / "data" / "test"

    verified_scopes: list[str] = []
    unverified_scopes: list[str] = []

    # 1. Manifest & Dataset Audit
    manifest_info = audit_manifest(manifest_p, data_dir=data_dir if data_dir.is_dir() else None)
    verified_scopes.append("configs/test_manifest.json (781 samples, structure & SHA-256 formats)")

    if manifest_info["images_present"]:
        verified_scopes.append(f"Image dataset files ({manifest_info['verified_image_files']}/781 content SHA-256 verified)")
    else:
        unverified_scopes.append("Image dataset files (raw 781-image content verification: NOT_RUN / UNAVAILABLE on clean checkout)")

    # 2. Model Audit
    metadata_files = [
        repo_root / "results" / "clean" / "cnn_baseline_metadata.json",
        repo_root / "results" / "clean" / "mobilenet_metadata.json",
        repo_root / "results" / "attacks" / "provisional" / "fgsm_cnn_metadata.json",
        repo_root / "results" / "attacks" / "provisional" / "fgsm_mobilenet_metadata.json",
    ]
    model_audit_info = audit_models(manifest_info["manifest_models"], metadata_files, repo_root=repo_root)
    verified_scopes.append("Model SHA-256 metadata consistency across manifest and evaluation metadata")

    any_disk_model = any(info["disk_file_present"] for info in model_audit_info.values())
    if any_disk_model:
        verified_scopes.append("Model binary files on disk (SHA-256 verified)")
    else:
        unverified_scopes.append("Model binary files on disk (local .h5 model binary hash recomputation: NOT_RUN / UNAVAILABLE on clean checkout)")

    # 3. Clean Evaluation Audit
    cnn_clean_path = repo_root / "results" / "clean" / "cnn_baseline_eval.csv"
    cnn_clean_summary = repo_root / "results" / "clean" / "cnn_baseline_summary.json"
    cnn_clean_res = audit_clean_evaluation(
        cnn_clean_path, summary_json_path=cnn_clean_summary
    )

    mob_clean_path = repo_root / "results" / "clean" / "mobilenet_eval.csv"
    mob_clean_summary = repo_root / "results" / "clean" / "mobilenet_summary.json"
    mob_clean_res = audit_clean_evaluation(
        mob_clean_path, summary_json_path=mob_clean_summary
    )

    verified_scopes.append(
        "CNN clean baseline results "
        f"(recalculated {cnn_clean_res['correct_count']}/{cnn_clean_res['total_samples']} correct, "
        f"accuracy {cnn_clean_res['accuracy']:.6f})"
    )
    verified_scopes.append(
        "MobileNetV2 clean baseline results "
        f"(recalculated {mob_clean_res['correct_count']}/{mob_clean_res['total_samples']} correct, "
        f"accuracy {mob_clean_res['accuracy']:.6f})"
    )

    # 4. FGSM Provisional Audit
    prov_dir = repo_root / "results" / "attacks" / "provisional"
    cnn_fgsm_res = audit_fgsm_results(
        prov_dir, "cnn", cnn_clean_res["correct_count"], cnn_clean_res["clean_correct_mask"]
    )
    mob_fgsm_res = audit_fgsm_results(
        prov_dir, "mobilenet", mob_clean_res["correct_count"], mob_clean_res["clean_correct_mask"]
    )

    cnn_epsilons = ", ".join(str(eps) for eps in sorted(cnn_fgsm_res))
    mob_epsilons = ", ".join(str(eps) for eps in sorted(mob_fgsm_res))
    verified_scopes.append(
        "CNN provisional FGSM results "
        f"(eps sweep {cnn_epsilons}, denominator {cnn_clean_res['correct_count']})"
    )
    verified_scopes.append(
        "MobileNetV2 provisional FGSM results "
        f"(eps sweep {mob_epsilons}, denominator {mob_clean_res['correct_count']})"
    )
    verified_scopes.append("Attack contracts (L_infinity <= epsilon + 1e-6, epsilon=0 invariants)")

    # 5. Cross-Document & Provenance Audit
    cross_doc_res = audit_cross_documents(
        repo_root=repo_root,
        clean_metrics={
            "cnn": cnn_clean_res,
            "mobilenet": mob_clean_res,
        },
        fgsm_metrics={
            "cnn": cnn_fgsm_res,
            "mobilenet": mob_fgsm_res,
        },
    )
    verified_scopes.append("Cross-document consistency (README, EXPERIMENT_CONTRACT, results docs, PROVENANCE.json)")

    # 6. Visual Review Evidence Audit
    evidence_dir = repo_root / "results" / "audit" / "evidence"
    visual_res = audit_visual_reviews(
        evidence_dir=evidence_dir,
        clean_cnn_csv=cnn_clean_path,
        clean_mobilenet_csv=mob_clean_path,
    )
    verified_scopes.append(
        "Strict visual-review evidence audit "
        f"({visual_res['total_candidates']} candidate samples dynamically verified across Taehee/Jaehyuk split files and combined file)"
    )

    report_data = {
        "audit_version": 1,
        "status": "PASSED",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_commit_sha": get_git_commit_sha(repo_root),
        "verified_scopes": verified_scopes,
        "unverified_scopes": unverified_scopes,
        "summary": {
            "clean_baseline": {
                "cnn_correct": cnn_clean_res["correct_count"],
                "cnn_accuracy": cnn_clean_res["accuracy"],
                "mobilenet_correct": mob_clean_res["correct_count"],
                "mobilenet_accuracy": mob_clean_res["accuracy"],
            },
            "fgsm_provisional": {
                "cnn_epsilons": {str(k): v for k, v in cnn_fgsm_res.items()},
                "mobilenet_epsilons": {str(k): v for k, v in mob_fgsm_res.items()},
            },
            "visual_review": {
                "total_candidates": visual_res["total_candidates"],
                "split_counts": visual_res["split_counts"],
                "reviewer_counts": visual_res["reviewer_counts"],
                "judgment_counts": visual_res["judgment_counts"],
                "class_distribution": visual_res["class_distribution"],
                "special_case_rows": visual_res["special_case_rows"],
                "candidate_rule": visual_res["candidate_rule"],
                "evidence_sha256": visual_res["evidence_sha256"],
            },
        },
    }

    if output_report_path:
        output_report_path.parent.mkdir(parents=True, exist_ok=True)
        output_report_path.write_text(
            json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return report_data
