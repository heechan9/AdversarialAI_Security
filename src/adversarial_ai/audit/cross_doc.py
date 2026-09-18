"""Cross-document verification module for checking numeric consistency and disclosures."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from adversarial_ai.audit.clean import audit_clean_evaluation
from adversarial_ai.audit.exceptions import AuditError


def _contains_numeric_close(text: str, expected: float, tolerance: float = 1e-6) -> bool:
    """Return whether text contains a decimal value numerically close to expected."""
    for token in re.findall(r"(?<![\w.])-?\d+\.\d+(?![\w.])", text):
        if abs(float(token) - expected) <= tolerance:
            return True
    return False


def audit_cross_documents(
    repo_root: Path = Path("."),
    clean_metrics: dict[str, Any] | None = None,
    fgsm_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cross-verify consistency across README, docs, metadata, CSVs, JSONs, and PROVENANCE.json."""
    checked_files: list[str] = []

    if clean_metrics is None:
        clean_metrics = {
            "cnn": audit_clean_evaluation(
                repo_root / "results" / "clean" / "cnn_baseline_eval.csv",
                summary_json_path=repo_root / "results" / "clean" / "cnn_baseline_summary.json",
            ),
            "mobilenet": audit_clean_evaluation(
                repo_root / "results" / "clean" / "mobilenet_eval.csv",
                summary_json_path=repo_root / "results" / "clean" / "mobilenet_summary.json",
            ),
        }

    # 1. Check required PROVENANCE.json
    prov_path = repo_root / "results" / "attacks" / "provisional" / "PROVENANCE.json"
    if not prov_path.is_file():
        raise AuditError(f"Required PROVENANCE.json is missing: {prov_path}")
    checked_files.append(str(prov_path))
    try:
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AuditError(
            f"Failed to read PROVENANCE.json: {prov_path}", {"error": str(exc)}
        ) from exc

    if not isinstance(prov, dict) or prov.get("status") != "provisional":
        status = prov.get("status") if isinstance(prov, dict) else None
        raise AuditError(f"PROVENANCE.json status must be 'provisional', got {status!r}")
    bundle = prov.get("bundle")
    bundle_sha = bundle.get("sha256") if isinstance(bundle, dict) else None
    if not isinstance(bundle_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", bundle_sha):
        raise AuditError("PROVENANCE.json bundle sha256 is missing or invalid")

    # 2. Check required README disclosures
    readme_path = repo_root / "README.md"
    if not readme_path.is_file():
        raise AuditError(f"Required README.md is missing: {readme_path}")
    checked_files.append(str(readme_path))
    readme_text = readme_path.read_text(encoding="utf-8")

    if clean_metrics:
        for model_name, metrics in clean_metrics.items():
            accuracy = metrics.get("accuracy")
            if not isinstance(accuracy, (int, float)):
                raise AuditError(f"Missing computed clean accuracy for {model_name}")
            if not _contains_numeric_close(readme_text, float(accuracy)):
                raise AuditError(
                    f"README.md does not contain the computed {model_name} accuracy",
                    {"computed_accuracy": accuracy},
                )

    limitation_keywords = ["MobileNet", "전처리"]
    if not all(kw in readme_text for kw in limitation_keywords):
        raise AuditError("README.md is missing required MobileNet preprocessing limitation disclosure")

    # 3. Check required docs/FGSM_PROVISIONAL_RESULTS.md claims
    fgsm_doc_path = repo_root / "docs" / "FGSM_PROVISIONAL_RESULTS.md"
    if not fgsm_doc_path.is_file():
        raise AuditError(f"Required FGSM results document is missing: {fgsm_doc_path}")
    checked_files.append(str(fgsm_doc_path))
    fgsm_doc = fgsm_doc_path.read_text(encoding="utf-8")

    expected_tokens = ["Provisional"]
    for metrics in clean_metrics.values():
        expected_tokens.append(str(metrics["correct_count"]))
        if not _contains_numeric_close(fgsm_doc, float(metrics["accuracy"])):
            raise AuditError(
                "docs/FGSM_PROVISIONAL_RESULTS.md is missing a computed clean accuracy",
                {"computed_accuracy": metrics["accuracy"]},
            )
    for token in expected_tokens:
        if token not in fgsm_doc:
            raise AuditError(
                "docs/FGSM_PROVISIONAL_RESULTS.md is missing expected claim or metric "
                f"token: {token!r}"
            )

    # 4. Cross-check passed clean_metrics if provided
    if clean_metrics and fgsm_metrics:
        for model_name, clean_result in clean_metrics.items():
            expected_denominator = clean_result.get("correct_count")
            model_fgsm = fgsm_metrics.get(model_name, {})
            for epsilon, result in model_fgsm.items():
                actual_denominator = result.get("asr_denominator")
                if actual_denominator != expected_denominator:
                    raise AuditError(
                        f"Cross-doc check failed for {model_name} eps={epsilon}: "
                        "FGSM denominator disagrees with computed clean-correct count",
                        {
                            "clean_correct_count": expected_denominator,
                            "fgsm_denominator": actual_denominator,
                        },
                    )

    return {
        "checked_files": checked_files,
        "provenance_verified": True,
        "readme_claims_verified": True,
        "fgsm_doc_claims_verified": True,
    }
