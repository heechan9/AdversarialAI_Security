"""Audit clean evaluation results dynamically from CSV and JSON evidence files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from adversarial_ai.audit.exceptions import AuditError

EXPECTED_TEST_SAMPLES = 781
CANONICAL_CLEAN_COUNTS = {
    "cnn": 504,
    "mobilenet": 613,
}


def audit_clean_evaluation(
    eval_csv_path: Path,
    summary_json_path: Path | None = None,
    report_csv_path: Path | None = None,
    expected_model_key: str | None = None,
) -> dict[str, Any]:
    """Dynamically recalculate correct count and accuracy from clean prediction CSV.

    Validates against expected model counts (CNN 504, MobileNet 613) and summary JSON.
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

    # Verify correct boolean calculation
    computed_correct_bool = df["true_label"] == df["predicted_label"]
    mismatched_correct = (df["correct"].astype(bool) != computed_correct_bool).sum()
    if mismatched_correct > 0:
        raise AuditError(
            f"Clean evaluation CSV contains {mismatched_correct} rows where 'correct' column disagrees with true_label == predicted_label",
            {"mismatched_rows": int(mismatched_correct)},
        )

    correct_count = int(computed_correct_bool.sum())
    calculated_accuracy = float(correct_count / EXPECTED_TEST_SAMPLES)

    # Match canonical expectations
    if expected_model_key is not None:
        key = expected_model_key.lower()
        if key in CANONICAL_CLEAN_COUNTS:
            canonical_expected = CANONICAL_CLEAN_COUNTS[key]
            if correct_count != canonical_expected:
                raise AuditError(
                    f"Clean correct count for {expected_model_key} must be {canonical_expected}/781, got {correct_count}/781",
                    {"expected": canonical_expected, "actual": correct_count, "model": expected_model_key},
                )

    # Cross-verify with summary JSON if available
    if summary_json_path is not None and summary_json_path.is_file():
        try:
            summary = json.loads(summary_json_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AuditError(f"Failed to read clean summary JSON: {summary_json_path}", {"error": str(exc)}) from exc

        summary_correct = summary.get("correct_count")
        summary_acc = summary.get("accuracy") or summary.get("test_accuracy")

        if summary_correct is not None and summary_correct != correct_count:
            raise AuditError(
                f"Summary JSON correct_count ({summary_correct}) disagrees with computed evaluation CSV ({correct_count})",
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
    }
