"""Audit clean evaluation results dynamically from CSV and JSON evidence files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.validation import (
    normalize_relative_path,
    parse_strict_booleans,
    require_nonempty_strings,
)

EXPECTED_TEST_SAMPLES = 781


def audit_clean_evaluation(
    eval_csv_path: Path,
    summary_json_path: Path | None = None,
    report_csv_path: Path | None = None,
    expected_relative_paths: list[str] | None = None,
    expected_true_labels: list[str] | None = None,
) -> dict[str, Any]:
    """Dynamically recalculate correct count and accuracy from clean prediction CSV.

    Validates against expected model metrics dynamically derived from canonical summary JSON.
    """
    if not eval_csv_path.is_file():
        raise AuditError(f"Clean evaluation CSV file missing: {eval_csv_path}")

    try:
        df = pd.read_csv(eval_csv_path)
    except Exception as exc:
        raise AuditError(f"Failed to read clean evaluation CSV: {eval_csv_path}", {"error": str(exc)}) from exc

    required_cols = {"relative_path", "true_label", "predicted_label", "correct"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise AuditError(f"Clean evaluation CSV missing required columns: {sorted(missing_cols)}")

    if len(df) != EXPECTED_TEST_SAMPLES:
        raise AuditError(
            f"Clean evaluation CSV row count must be {EXPECTED_TEST_SAMPLES}, got {len(df)}",
            {"expected": EXPECTED_TEST_SAMPLES, "actual": len(df)},
        )

    relative_paths = [
        normalize_relative_path(value, f"clean.relative_path[{index}]")
        for index, value in enumerate(df["relative_path"].tolist())
    ]
    if len(relative_paths) != len(set(relative_paths)):
        raise AuditError("Clean evaluation CSV contains duplicate relative paths")
    true_labels = require_nonempty_strings(df["true_label"].tolist(), "clean.true_label")
    predicted_labels = require_nonempty_strings(
        df["predicted_label"].tolist(), "clean.predicted_label"
    )
    if (expected_relative_paths is None) != (expected_true_labels is None):
        raise AuditError("Clean canonical validation requires both paths and true labels")
    if expected_relative_paths is not None:
        if relative_paths != expected_relative_paths:
            raise AuditError("Clean evaluation path order disagrees with the manifest")
        if true_labels != expected_true_labels:
            raise AuditError("Clean evaluation true labels disagree with the manifest")

    # Verify correct boolean calculation in CSV
    computed_correct_bool = df["true_label"] == df["predicted_label"]
    declared_correct = parse_strict_booleans(df["correct"].tolist(), "clean.correct")
    mismatched_correct = sum(
        declared != computed
        for declared, computed in zip(declared_correct, computed_correct_bool.tolist())
    )
    if mismatched_correct > 0:
        raise AuditError(
            f"Clean evaluation CSV contains {mismatched_correct} rows where 'correct' column disagrees with true_label == predicted_label",
            {"mismatched_rows": int(mismatched_correct)},
        )

    correct_count = int(computed_correct_bool.sum())
    calculated_accuracy = float(correct_count / EXPECTED_TEST_SAMPLES)

    # Cross-verify dynamically with canonical summary JSON if available
    if summary_json_path is not None:
        if not summary_json_path.is_file():
            raise AuditError(f"Clean summary JSON file missing: {summary_json_path}")
        try:
            summary = json.loads(summary_json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AuditError(f"Failed to read clean summary JSON: {summary_json_path}", {"error": str(exc)}) from exc

        summary_correct = summary.get("correct_predictions") if "correct_predictions" in summary else summary.get("correct_count")
        summary_acc = summary.get("test_accuracy") if "test_accuracy" in summary else summary.get("accuracy")

        if summary_correct is not None and summary_correct != correct_count:
            raise AuditError(
                f"Summary JSON correct count ({summary_correct}) disagrees with computed evaluation CSV ({correct_count})",
                {"summary_correct": summary_correct, "computed_correct": correct_count},
            )

        if summary_acc is not None and abs(summary_acc - calculated_accuracy) > 1e-6:
            raise AuditError(
                f"Summary JSON accuracy ({summary_acc}) disagrees with computed accuracy ({calculated_accuracy})",
                {"summary_acc": summary_acc, "calculated_accuracy": calculated_accuracy},
            )

    return {
        "eval_csv_path": str(eval_csv_path),
        "total_samples": EXPECTED_TEST_SAMPLES,
        "correct_count": correct_count,
        "accuracy": calculated_accuracy,
        "clean_correct_mask": computed_correct_bool.tolist(),
        "relative_paths": relative_paths,
        "true_labels": true_labels,
        "predicted_labels": predicted_labels,
    }
