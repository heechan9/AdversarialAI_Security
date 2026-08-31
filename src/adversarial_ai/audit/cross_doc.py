"""Cross-document verification module for checking numeric consistency and disclosures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adversarial_ai.audit.exceptions import AuditError


def audit_cross_documents(
    repo_root: Path = Path("."),
    clean_metrics: dict[str, Any] | None = None,
    fgsm_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cross-verify consistency across README, docs, metadata, CSVs, JSONs, and PROVENANCE.json."""
    checked_files: list[str] = []

    # 1. Check PROVENANCE.json if present
    prov_path = repo_root / "results" / "attacks" / "provisional" / "PROVENANCE.json"
    if prov_path.is_file():
        checked_files.append(str(prov_path))
        try:
            prov = json.loads(prov_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AuditError(f"Failed to read PROVENANCE.json: {prov_path}", {"error": str(exc)}) from exc

        if prov.get("status") != "provisional":
            raise AuditError(
                f"PROVENANCE.json status must be 'provisional', got {prov.get('status')!r}"
            )
        bundle = prov.get("bundle")
        if not isinstance(bundle, dict) or not bundle.get("sha256"):
            raise AuditError("PROVENANCE.json bundle sha256 is missing or invalid")

    # 2. Check README disclosures
    readme_path = repo_root / "README.md"
    if readme_path.is_file():
        checked_files.append(str(readme_path))
        readme_text = readme_path.read_text(encoding="utf-8")

        # Verify CNN baseline accuracy claim in README
        if "0.6453264951705933" not in readme_text:
            raise AuditError("README.md does not contain canonical CNN accuracy claim '0.6453264951705933'")

        # Verify MobileNet finetuned accuracy claim in README
        if "0.7848911881446838" not in readme_text:
            raise AuditError("README.md does not contain canonical MobileNet accuracy claim '0.7848911881446838'")

        # Verify MobileNet preprocessing limitation disclosure
        limitation_keywords = [
            "MobileNet",
            "전처리",
        ]
        if not all(kw in readme_text for kw in limitation_keywords):
            raise AuditError("README.md is missing required MobileNet preprocessing limitation disclosure")

    # 3. Check docs/FGSM_PROVISIONAL_RESULTS.md claims
    fgsm_doc_path = repo_root / "docs" / "FGSM_PROVISIONAL_RESULTS.md"
    if fgsm_doc_path.is_file():
        checked_files.append(str(fgsm_doc_path))
        fgsm_doc = fgsm_doc_path.read_text(encoding="utf-8")

        expected_tokens = [
            "0.645327",
            "0.784891",
            "504",
            "613",
            "Provisional",
        ]
        for token in expected_tokens:
            if token not in fgsm_doc:
                raise AuditError(
                    f"docs/FGSM_PROVISIONAL_RESULTS.md is missing expected claim or metric token: {token!r}"
                )

    # 4. Cross-check passed clean_metrics if provided
    if clean_metrics:
        cnn_clean = clean_metrics.get("cnn", {})
        if cnn_clean.get("correct_count") != 504:
            raise AuditError(
                f"Cross-doc check failed: CNN clean correct count {cnn_clean.get('correct_count')} != 504"
            )
        mob_clean = clean_metrics.get("mobilenet", {})
        if mob_clean.get("correct_count") != 613:
            raise AuditError(
                f"Cross-doc check failed: MobileNet clean correct count {mob_clean.get('correct_count')} != 613"
            )

    return {
        "checked_files": checked_files,
        "provenance_verified": prov_path.is_file(),
        "readme_claims_verified": readme_path.is_file(),
        "fgsm_doc_claims_verified": fgsm_doc_path.is_file(),
    }
