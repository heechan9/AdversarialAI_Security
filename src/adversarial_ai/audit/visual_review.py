"""Strict visual review evidence verification module.

Validates authoritative visual review CSV files against canonical Clean baseline evaluations.
Verifies schema compliance, UTF-8 BOM encoding, non-empty fields, reviewer split disjointness,
combined file union equality, unique non-generic visual notes, allowed Korean judgments,
and cross-checks predictions and confidences against canonical Clean baseline CSVs.
"""

from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import math
import re
from pathlib import Path
from typing import Any

from adversarial_ai.audit.exceptions import AuditError

ALLOWED_JUDGMENTS = {"라벨 정확", "라벨 오류 의심", "판단 보류"}
UTF8_BOM = b"\xef\xbb\xbf"
EVIDENCE_MANIFEST = "manifest.json"

SPLIT_REQUIRED_FIELDS = [
    "file_path",
    "current_label",
    "cnn_prediction",
    "cnn_confidence",
    "mnv2_prediction",
    "mnv2_confidence",
    "판정",
    "검토자",
    "검토일",
    "비고",
]

COMBINED_REQUIRED_FIELDS = SPLIT_REQUIRED_FIELDS + ["엄격검증_기준"]


def load_review_csv(file_path: Path, required_fields: list[str]) -> list[dict[str, str]]:
    """Load a review CSV with a required UTF-8 BOM and exact ordered schema."""
    if not file_path.is_file():
        raise AuditError(f"Visual review file missing: {file_path}")

    try:
        raw = file_path.read_bytes()
        if not raw.startswith(UTF8_BOM):
            raise AuditError(f"Visual review file is missing required UTF-8 BOM: {file_path}")
        content = raw.decode("utf-8-sig")
    except Exception as e:
        if isinstance(e, AuditError):
            raise
        raise AuditError(f"Visual review file failed UTF-8 read: {file_path} - {e}") from e

    reader = csv.DictReader(io.StringIO(content, newline=""))
    if not reader.fieldnames:
        raise AuditError(f"Visual review file has empty header: {file_path}")

    if reader.fieldnames != required_fields:
        raise AuditError(
            f"Visual review file {file_path.name} schema mismatch: "
            f"expected {required_fields}, got {reader.fieldnames}"
        )

    rows = list(reader)
    if not rows:
        raise AuditError(f"Visual review file is empty: {file_path}")

    return rows


def _load_evidence_manifest(evidence_dir: Path) -> dict[str, Any]:
    manifest_path = evidence_dir / EVIDENCE_MANIFEST
    if not manifest_path.is_file():
        raise AuditError(f"Visual review evidence manifest missing: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"Invalid visual review evidence manifest: {manifest_path}") from exc
    if not isinstance(data, dict):
        raise AuditError("Visual review evidence manifest must be a JSON object")
    if data.get("schema_version") != 1:
        raise AuditError("Unsupported visual review evidence manifest schema_version")
    return data


def _verify_evidence_hashes(
    evidence_dir: Path, manifest: dict[str, Any], expected_names: set[str]
) -> dict[str, str]:
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != expected_names:
        actual_names = sorted(files) if isinstance(files, dict) else files
        raise AuditError(
            "Visual review evidence manifest file set mismatch",
            {"expected": sorted(expected_names), "actual": actual_names},
        )

    verified: dict[str, str] = {}
    for name in sorted(expected_names):
        entry = files.get(name)
        expected_sha = entry.get("sha256") if isinstance(entry, dict) else None
        if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            raise AuditError(f"Invalid SHA-256 entry for visual review file: {name}")
        actual_sha = hashlib.sha256((evidence_dir / name).read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            raise AuditError(
                f"Visual review evidence SHA-256 mismatch for {name}",
                {"expected": expected_sha, "actual": actual_sha},
            )
        verified[name] = actual_sha
    return verified


def derive_candidate_rows(
    clean_cnn_csv: Path,
    clean_mobilenet_csv: Path,
    confidence_threshold: float = 0.70,
) -> dict[str, dict[str, Any]]:
    """Dynamically derive candidate set from clean baseline evaluations using unrounded confidences.

    Candidates satisfy:
    1. both models predict the same class (cnn_prediction == mnv2_prediction),
    2. that shared prediction differs from true_label,
    3. both unrounded predicted-class confidences are >= confidence_threshold (0.70).
    """
    if not clean_cnn_csv.is_file():
        raise AuditError(f"Clean CNN CSV missing: {clean_cnn_csv}")
    if not clean_mobilenet_csv.is_file():
        raise AuditError(f"Clean MobileNet CSV missing: {clean_mobilenet_csv}")

    try:
        cnn_rows = list(
            csv.DictReader(io.StringIO(clean_cnn_csv.read_text(encoding="utf-8-sig")))
        )
        mob_rows = list(
            csv.DictReader(
                io.StringIO(clean_mobilenet_csv.read_text(encoding="utf-8-sig"))
            )
        )
    except (UnicodeDecodeError, csv.Error) as exc:
        raise AuditError("Failed to parse canonical Clean evaluation CSV") from exc

    for model_name, rows in (("CNN", cnn_rows), ("MobileNetV2", mob_rows)):
        paths = [r.get("relative_path", "") for r in rows]
        if any(not path for path in paths):
            raise AuditError(f"Canonical {model_name} Clean CSV contains an empty path")
        if len(paths) != len(set(paths)):
            raise AuditError(f"Canonical {model_name} Clean CSV contains duplicate paths")

    mob_by_path = {r["relative_path"]: r for r in mob_rows}
    cnn_paths = {r["relative_path"] for r in cnn_rows}
    if cnn_paths != set(mob_by_path):
        raise AuditError("Canonical Clean CSV path sets do not match")

    candidates = {}
    for cnn_r in cnn_rows:
        rel_path = cnn_r["relative_path"]
        if rel_path not in mob_by_path:
            raise AuditError(f"Path {rel_path} in Clean CNN CSV not found in Clean MobileNet CSV")

        mob_r = mob_by_path[rel_path]

        true_label = cnn_r["true_label"]
        if mob_r["true_label"] != true_label:
            raise AuditError(f"Mismatched true label for {rel_path} between clean CSVs")

        cnn_pred = cnn_r["predicted_label"]
        mob_pred = mob_r["predicted_label"]

        try:
            cnn_prob_col = f"prob_{int(cnn_r['predicted_index'])}_{cnn_pred}"
            mob_prob_col = f"prob_{int(mob_r['predicted_index'])}_{mob_pred}"
            cnn_conf_raw = float(cnn_r[cnn_prob_col])
            mob_conf_raw = float(mob_r[mob_prob_col])
        except (KeyError, TypeError, ValueError) as exc:
            raise AuditError(
                f"Canonical Clean CSV has invalid predicted-class confidence for {rel_path}"
            ) from exc
        if not all(
            math.isfinite(value) and 0.0 <= value <= 1.0
            for value in (cnn_conf_raw, mob_conf_raw)
        ):
            raise AuditError(
                f"Canonical Clean CSV confidence is outside [0, 1] for {rel_path}"
            )

        if cnn_pred == mob_pred and cnn_pred != true_label:
            if cnn_conf_raw >= confidence_threshold and mob_conf_raw >= confidence_threshold:
                candidates[rel_path] = {
                    "file_path": rel_path,
                    "current_label": true_label,
                    "cnn_prediction": cnn_pred,
                    "cnn_confidence_raw": cnn_conf_raw,
                    "mnv2_prediction": mob_pred,
                    "mnv2_confidence_raw": mob_conf_raw,
                }

    return candidates


def audit_visual_reviews(
    evidence_dir: Path,
    clean_cnn_csv: Path,
    clean_mobilenet_csv: Path,
    confidence_threshold: float = 0.70,
) -> dict[str, Any]:
    """Audit strict visual review evidence CSVs against canonical Clean baseline evaluations.

    Validates schema, split disjointness, union equality, dynamic candidate set equality,
    unique non-generic notes, allowed Korean judgments, non-empty criteria, and row-level
    agreement with canonical Clean predictions and confidences.
    """
    taehee_file = evidence_dir / "review_taehee_visual_strict_final.csv"
    jaehyuk_file = evidence_dir / "review_jaehyuk_visual_strict_final.csv"
    combined_file = evidence_dir / "63_images_strict_visual_audit.csv"
    evidence_files = {taehee_file.name, jaehyuk_file.name, combined_file.name}
    manifest = _load_evidence_manifest(evidence_dir)

    candidate_rule = manifest.get("candidate_rule")
    if not isinstance(candidate_rule, dict):
        raise AuditError("Visual review evidence manifest is missing candidate_rule")
    manifest_threshold = candidate_rule.get("confidence_threshold")
    rounding_decimals = candidate_rule.get("confidence_rounding_decimals")
    if manifest_threshold != confidence_threshold:
        raise AuditError(
            "Visual review confidence threshold disagrees with evidence manifest",
            {"manifest": manifest_threshold, "requested": confidence_threshold},
        )
    if (
        not isinstance(rounding_decimals, int)
        or isinstance(rounding_decimals, bool)
        or rounding_decimals < 0
        or rounding_decimals > 12
    ):
        raise AuditError("Visual review evidence manifest has invalid confidence rounding decimals")

    taehee_rows = load_review_csv(taehee_file, SPLIT_REQUIRED_FIELDS)
    jaehyuk_rows = load_review_csv(jaehyuk_file, SPLIT_REQUIRED_FIELDS)
    combined_rows = load_review_csv(combined_file, COMBINED_REQUIRED_FIELDS)

    # Validate row constraints, Korean headers, non-empty fields, notes uniqueness
    _validate_row_constraints(taehee_file.name, taehee_rows, expected_reviewer="김태희")
    _validate_row_constraints(jaehyuk_file.name, jaehyuk_rows, expected_reviewer="이재혁")
    _validate_row_constraints(
        combined_file.name, combined_rows, expected_reviewer=None, check_criteria=True
    )

    criteria_values = {r["엄격검증_기준"].strip() for r in combined_rows}
    if len(criteria_values) != 1:
        raise AuditError("Combined visual review file contains inconsistent 엄격검증_기준 values")

    taehee_paths = [r["file_path"] for r in taehee_rows]
    jaehyuk_paths = [r["file_path"] for r in jaehyuk_rows]
    combined_paths = [r["file_path"] for r in combined_rows]

    # Unique paths within split and combined files
    if len(set(taehee_paths)) != len(taehee_paths):
        raise AuditError(f"Duplicate file_path found in {taehee_file.name}")
    if len(set(jaehyuk_paths)) != len(jaehyuk_paths):
        raise AuditError(f"Duplicate file_path found in {jaehyuk_file.name}")
    if len(set(combined_paths)) != len(combined_paths):
        raise AuditError(f"Duplicate file_path found in {combined_file.name}")

    # Split disjointness
    overlap = set(taehee_paths) & set(jaehyuk_paths)
    if overlap:
        raise AuditError(f"Split review files are not disjoint; overlapping paths: {sorted(overlap)}")

    # Split union vs combined file row-for-row equality on shared columns
    split_rows_map = {r["file_path"]: r for r in taehee_rows + jaehyuk_rows}
    combined_rows_map = {r["file_path"]: r for r in combined_rows}

    if set(split_rows_map.keys()) != set(combined_rows_map.keys()):
        raise AuditError("Set of paths in split files does not match combined review file")

    for path, split_r in split_rows_map.items():
        comb_r = combined_rows_map[path]
        for field in SPLIT_REQUIRED_FIELDS:
            if split_r[field] != comb_r[field]:
                raise AuditError(
                    f"Drift between split and combined review for path {path} on field {field}: "
                    f"split='{split_r[field]}' vs combined='{comb_r[field]}'"
                )

    # Candidate Derivation & Verification
    candidates = derive_candidate_rows(clean_cnn_csv, clean_mobilenet_csv, confidence_threshold)

    review_paths_set = set(combined_paths)
    candidate_paths_set = set(candidates.keys())

    if review_paths_set != candidate_paths_set:
        missing_in_review = candidate_paths_set - review_paths_set
        extra_in_review = review_paths_set - candidate_paths_set
        raise AuditError(
            f"Review file candidate set discrepancy! "
            f"Missing in review: {sorted(missing_in_review)}, Extra in review: {sorted(extra_in_review)}"
        )

    # Canonical Cross-Check for every row
    for r in combined_rows:
        path = r["file_path"]
        cand = candidates[path]

        if r["current_label"] != cand["current_label"]:
            raise AuditError(
                f"Row {path}: current_label '{r['current_label']}' != canonical '{cand['current_label']}'"
            )

        if r["cnn_prediction"] != cand["cnn_prediction"]:
            raise AuditError(
                f"Row {path}: cnn_prediction '{r['cnn_prediction']}' != canonical '{cand['cnn_prediction']}'"
            )

        if r["mnv2_prediction"] != cand["mnv2_prediction"]:
            raise AuditError(
                f"Row {path}: mnv2_prediction '{r['mnv2_prediction']}' != canonical '{cand['mnv2_prediction']}'"
            )

        try:
            r_cnn_conf = float(r["cnn_confidence"])
            r_mnv2_conf = float(r["mnv2_confidence"])
        except ValueError as e:
            raise AuditError(f"Row {path}: non-numeric confidence values") from e
        if not all(math.isfinite(value) for value in (r_cnn_conf, r_mnv2_conf)):
            raise AuditError(f"Row {path}: non-finite confidence values")

        expected_cnn_conf = round(cand["cnn_confidence_raw"], rounding_decimals)
        if r_cnn_conf != expected_cnn_conf:
            raise AuditError(
                f"Row {path}: cnn_confidence {r_cnn_conf} != canonical raw value "
                f"rounded to {rounding_decimals} decimals ({expected_cnn_conf})"
            )

        expected_mnv2_conf = round(cand["mnv2_confidence_raw"], rounding_decimals)
        if r_mnv2_conf != expected_mnv2_conf:
            raise AuditError(
                f"Row {path}: mnv2_confidence {r_mnv2_conf} != canonical raw value "
                f"rounded to {rounding_decimals} decimals ({expected_mnv2_conf})"
            )

    evidence_sha256 = _verify_evidence_hashes(evidence_dir, manifest, evidence_files)

    # Dynamic counts for summary reporting
    reviewer_counts: dict[str, int] = {}
    judgment_counts: dict[str, int] = {}
    class_distribution: dict[str, int] = {}

    for r in combined_rows:
        rev = r["검토자"]
        j = r["판정"]
        lbl = r["current_label"]

        reviewer_counts[rev] = reviewer_counts.get(rev, 0) + 1
        judgment_counts[j] = judgment_counts.get(j, 0) + 1
        class_distribution[lbl] = class_distribution.get(lbl, 0) + 1

    special_case_rows = [
        {"file_path": r["file_path"], "judgment": r["판정"]}
        for r in combined_rows
        if r["판정"] != "라벨 정확"
    ]

    return {
        "status": "PASSED",
        "total_candidates": len(combined_rows),
        "split_counts": {
            "taehee": len(taehee_rows),
            "jaehyuk": len(jaehyuk_rows),
        },
        "reviewer_counts": reviewer_counts,
        "judgment_counts": judgment_counts,
        "class_distribution": class_distribution,
        "special_case_rows": special_case_rows,
        "candidate_rule": {
            "confidence_threshold": confidence_threshold,
            "confidence_rounding_decimals": rounding_decimals,
        },
        "evidence_sha256": evidence_sha256,
    }


def _validate_row_constraints(
    file_name: str,
    rows: list[dict[str, str]],
    expected_reviewer: str | None,
    check_criteria: bool = False,
) -> None:
    """Validate constraints for review rows."""
    notes_seen = set()

    for i, r in enumerate(rows):
        path = r.get("file_path", "")
        for field, value in r.items():
            if field is None:
                raise AuditError(
                    f"File {file_name} row {i+1}: unexpected values beyond declared schema"
                )
            if not isinstance(value, str) or not value.strip():
                raise AuditError(
                    f"File {file_name} row {i+1} ({path or 'unknown path'}): "
                    f"empty required field '{field}'"
                )

        if expected_reviewer and r.get("검토자") != expected_reviewer:
            raise AuditError(
                f"File {file_name} row {i+1} ({path}): reviewer '{r.get('검토자')}' != expected '{expected_reviewer}'"
            )

        j = r.get("판정", "")
        if j not in ALLOWED_JUDGMENTS:
            raise AuditError(f"File {file_name} row {i+1} ({path}): invalid judgment '{j}'")

        notes = r.get("비고", "")
        if not notes or not notes.strip():
            raise AuditError(f"File {file_name} row {i+1} ({path}): blank 비고 notes")

        normalized_notes = " ".join(notes.split())
        if normalized_notes in notes_seen:
            raise AuditError(
                f"File {file_name} row {i+1} ({path}): duplicate/generic 비고 note found ('{notes[:30]}...')"
            )
        notes_seen.add(normalized_notes)

        if check_criteria:
            crit = r.get("엄격검증_기준", "")
            if not crit or not crit.strip():
                raise AuditError(f"File {file_name} row {i+1} ({path}): blank 엄격검증_기준")

        review_date = r.get("검토일", "")
        try:
            parsed_date = datetime.date.fromisoformat(review_date)
        except ValueError as exc:
            raise AuditError(
                f"File {file_name} row {i+1} ({path}): invalid ISO review date '{review_date}'"
            ) from exc
        if parsed_date.isoformat() != review_date:
            raise AuditError(
                f"File {file_name} row {i+1} ({path}): review date must use YYYY-MM-DD"
            )

        try:
            cnn_c = float(r["cnn_confidence"])
            mnv2_c = float(r["mnv2_confidence"])
        except (KeyError, ValueError) as e:
            raise AuditError(f"File {file_name} row {i+1} ({path}): invalid confidence values") from e

        if not (0.0 <= cnn_c <= 1.0) or not (0.0 <= mnv2_c <= 1.0):
            raise AuditError(
                f"File {file_name} row {i+1} ({path}): confidence values out of range [0, 1]"
            )
