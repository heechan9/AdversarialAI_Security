"""Audit provisional FGSM attack results, sample CSVs, report JSONs, and attack contract compliance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.validation import (
    normalize_relative_path,
    parse_finite_numbers,
    parse_strict_booleans,
    require_nonempty_strings,
)

EXPECTED_TEST_SAMPLES = 781
EXPECTED_EPSILONS = [0.0, 0.01, 0.03, 0.05]
SAMPLE_COLUMNS = [
    "relative_path",
    "epsilon",
    "true_index",
    "true_label",
    "clean_predicted_index",
    "clean_predicted_label",
    "adversarial_predicted_index",
    "adversarial_predicted_label",
    "clean_correct",
    "attack_success",
    "linf",
]
SUMMARY_COLUMNS = [
    "epsilon",
    "test_samples",
    "clean_accuracy",
    "robust_accuracy",
    "accuracy_drop",
    "macro_f1",
    "untargeted_asr",
    "attack_successes",
    "asr_denominator_clean_correct",
    "linf_max",
    "linf_mean",
]


def _numeric_close(
    actual: Any, expected: float, context: str, *, tolerance: float = 1e-12
) -> None:
    value = parse_finite_numbers([actual], context)[0]
    if abs(value - expected) > tolerance:
        raise AuditError(
            f"{context} disagrees with sample-level evidence",
            {"reported": value, "recalculated": expected},
        )


def audit_fgsm_results(
    provisional_dir: Path,
    model_name: str,
    clean_correct_count: int,
    clean_correct_mask: list[bool] | None = None,
    clean_relative_paths: list[str] | None = None,
    clean_true_labels: list[str] | None = None,
    clean_predicted_labels: list[str] | None = None,
) -> dict[str, Any]:
    """Audit provisional FGSM evaluation CSVs and reports for a given model ('cnn' or 'mobilenet').

    Verifies:
    1. Sample CSV row counts, columns, and metric calculations.
    2. ASR denominator matches clean-correct count exactly.
    3. Attack contracts:
       - L_infinity <= epsilon + 1e-6
       - At epsilon=0: drop=0, ASR=0, attack_successes=0, linf_max=0
    4. Report JSON metrics consistency with CSV recalculated metrics.
    """
    if not provisional_dir.is_dir():
        raise AuditError(f"Provisional results directory missing: {provisional_dir}")
    if model_name not in {"cnn", "mobilenet"}:
        raise AuditError(f"Unsupported FGSM model name: {model_name!r}")
    if clean_correct_count <= 0:
        raise AuditError("FGSM clean-correct denominator must be positive")

    clean_context = (clean_relative_paths, clean_true_labels, clean_predicted_labels)
    if any(value is not None for value in clean_context) and not all(
        value is not None for value in clean_context
    ):
        raise AuditError(
            "FGSM canonical row validation requires paths, true labels, and clean predictions"
        )

    summary_csv = provisional_dir / f"fgsm_{model_name}.csv"
    if not summary_csv.is_file():
        raise AuditError(f"FGSM model summary CSV missing: {summary_csv}")
    try:
        summary_frame = pd.read_csv(summary_csv)
    except Exception as exc:
        raise AuditError(
            f"Failed to read FGSM model summary CSV: {summary_csv}",
            {"error": str(exc)},
        ) from exc
    if list(summary_frame.columns) != SUMMARY_COLUMNS:
        raise AuditError(f"FGSM model summary CSV schema mismatch: {summary_csv}")
    summary_epsilons = parse_finite_numbers(
        summary_frame["epsilon"].tolist(), f"fgsm[{model_name}].summary.epsilon",
        minimum=0.0,
    )
    if len(summary_frame) != len(EXPECTED_EPSILONS) or summary_epsilons != EXPECTED_EPSILONS:
        raise AuditError(
            f"FGSM model summary epsilon rows disagree with canonical sweep: {summary_csv}"
        )

    audited_epsilons: dict[float, dict[str, Any]] = {}

    for eps in EXPECTED_EPSILONS:
        # Check integer/float formatting in filename
        eps_str = "0" if eps == 0.0 else str(eps)
        sample_csv = provisional_dir / f"fgsm_{model_name}_eps_{eps_str}_samples.csv"
        report_json = provisional_dir / f"fgsm_{model_name}_eps_{eps_str}_report.json"

        if not sample_csv.is_file():
            raise AuditError(f"FGSM sample CSV missing for {model_name} eps={eps}: {sample_csv}")
        if not report_json.is_file():
            raise AuditError(f"FGSM report JSON missing for {model_name} eps={eps}: {report_json}")

        try:
            df = pd.read_csv(sample_csv)
        except Exception as exc:
            raise AuditError(f"Failed to read FGSM sample CSV: {sample_csv}", {"error": str(exc)}) from exc

        if list(df.columns) != SAMPLE_COLUMNS:
            raise AuditError(f"FGSM sample CSV schema mismatch: {sample_csv}")

        if len(df) != EXPECTED_TEST_SAMPLES:
            raise AuditError(
                f"FGSM sample CSV row count for {model_name} eps={eps} must be {EXPECTED_TEST_SAMPLES}, got {len(df)}",
                {"expected": EXPECTED_TEST_SAMPLES, "actual": len(df)},
            )

        relative_paths = [
            normalize_relative_path(
                value, f"fgsm[{model_name}][{eps}].relative_path[{index}]"
            )
            for index, value in enumerate(df["relative_path"].tolist())
        ]
        if len(relative_paths) != len(set(relative_paths)):
            raise AuditError(
                f"FGSM sample CSV contains duplicate relative paths for {model_name} eps={eps}"
            )
        true_labels = require_nonempty_strings(
            df["true_label"].tolist(), f"fgsm[{model_name}][{eps}].true_label"
        )
        clean_predictions = require_nonempty_strings(
            df["clean_predicted_label"].tolist(),
            f"fgsm[{model_name}][{eps}].clean_predicted_label",
        )
        adversarial_predictions = require_nonempty_strings(
            df["adversarial_predicted_label"].tolist(),
            f"fgsm[{model_name}][{eps}].adversarial_predicted_label",
        )

        if clean_relative_paths is not None:
            if relative_paths != clean_relative_paths:
                raise AuditError(
                    f"FGSM sample path order disagrees with Clean baseline for {model_name} eps={eps}"
                )
            if true_labels != clean_true_labels:
                raise AuditError(
                    f"FGSM true labels disagree with Clean baseline for {model_name} eps={eps}"
                )
            if clean_predictions != clean_predicted_labels:
                raise AuditError(
                    f"FGSM clean predictions disagree with Clean baseline for {model_name} eps={eps}"
                )

        epsilon_values = parse_finite_numbers(
            df["epsilon"].tolist(), f"fgsm[{model_name}][{eps}].epsilon", minimum=0.0
        )
        if any(abs(value - eps) > 1e-12 for value in epsilon_values):
            raise AuditError(
                f"FGSM epsilon column disagrees with filename for {model_name} eps={eps}"
            )

        # Cross-check clean_correct mask if provided
        csv_clean_correct = parse_strict_booleans(
            df["clean_correct"].tolist(), f"fgsm[{model_name}][{eps}].clean_correct"
        )
        if clean_correct_mask is not None:
            if csv_clean_correct != clean_correct_mask:
                diff_count = sum(c1 != c2 for c1, c2 in zip(csv_clean_correct, clean_correct_mask))
                raise AuditError(
                    f"FGSM sample CSV clean_correct column disagrees with clean baseline eval CSV for {model_name} eps={eps} across {diff_count} samples",
                    {"diff_count": diff_count, "model": model_name, "epsilon": eps},
                )

        # Derived calculations
        clean_correct_derived = pd.Series(csv_clean_correct, dtype=bool)
        actual_clean_correct_count = int(sum(csv_clean_correct))

        if actual_clean_correct_count != clean_correct_count:
            raise AuditError(
                f"FGSM sample CSV clean-correct denominator ({actual_clean_correct_count}) differs from clean baseline expectation ({clean_correct_count})",
                {
                    "expected_denominator": clean_correct_count,
                    "actual_denominator": actual_clean_correct_count,
                    "model": model_name,
                    "epsilon": eps,
                },
            )

        # Check attack_success definition: must be clean_correct AND adversarial_predicted != true_label
        adv_correct_derived = pd.Series(
            [truth == prediction for truth, prediction in zip(true_labels, adversarial_predictions)],
            dtype=bool,
        )
        computed_attack_success = clean_correct_derived & (~adv_correct_derived)
        csv_attack_success = pd.Series(
            parse_strict_booleans(
                df["attack_success"].tolist(),
                f"fgsm[{model_name}][{eps}].attack_success",
            ),
            dtype=bool,
        )

        mismatched_success = (csv_attack_success != computed_attack_success).sum()
        if mismatched_success > 0:
            raise AuditError(
                f"FGSM sample CSV attack_success column disagrees with clean_correct & (adv_label != true_label) in {sample_csv}",
                {"mismatched_rows": int(mismatched_success)},
            )

        robust_correct_count = int(adv_correct_derived.sum())
        robust_accuracy = float(robust_correct_count / EXPECTED_TEST_SAMPLES)

        attack_success_count = int(computed_attack_success.sum())
        calculated_asr = float(attack_success_count / clean_correct_count) if clean_correct_count > 0 else 0.0

        # L_infinity validation
        linf_values = parse_finite_numbers(
            df["linf"].tolist(), f"fgsm[{model_name}][{eps}].linf", minimum=0.0
        )
        max_linf = max(linf_values)
        mean_linf = float(sum(linf_values) / EXPECTED_TEST_SAMPLES)

        if max_linf > eps + 1e-6:
            raise AuditError(
                f"L_infinity contract violation for {model_name} eps={eps}: max_linf {max_linf} > eps + 1e-6",
                {"epsilon": eps, "max_linf": max_linf, "allowed": eps + 1e-6},
            )

        # Epsilon = 0 contract
        if eps == 0.0:
            if max_linf > 1e-7:
                raise AuditError(
                    f"Contract violation for eps=0: max_linf must be 0, got {max_linf}",
                    {"max_linf": max_linf},
                )
            if attack_success_count != 0:
                raise AuditError(
                    f"Contract violation for eps=0: attack_success_count must be 0, got {attack_success_count}",
                    {"attack_success_count": attack_success_count},
                )
            if calculated_asr != 0.0:
                raise AuditError(
                    f"Contract violation for eps=0: ASR must be 0, got {calculated_asr}",
                    {"asr": calculated_asr},
                )
            if adversarial_predictions != clean_predictions:
                raise AuditError(
                    f"Contract violation for eps=0: adversarial predictions differ from clean predictions for {model_name}"
                )

        # Report JSON cross-verification
        try:
            report = json.loads(report_json.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AuditError(
                f"Failed to read report JSON: {report_json}", {"error": str(exc)}
            ) from exc
        if not isinstance(report, dict):
            raise AuditError(f"FGSM report JSON root must be an object: {report_json}")
        class_names = list(dict.fromkeys(true_labels))
        expected_report = classification_report(
            true_labels,
            adversarial_predictions,
            labels=class_names,
            target_names=class_names,
            output_dict=True,
            zero_division=0,
        )
        if set(report) != set(expected_report):
            raise AuditError(f"FGSM report JSON keys disagree with sample evidence: {report_json}")
        for section_name, expected_section in expected_report.items():
            actual_section = report.get(section_name)
            if isinstance(expected_section, dict):
                if not isinstance(actual_section, dict) or set(actual_section) != set(expected_section):
                    raise AuditError(
                        f"FGSM report section {section_name!r} schema mismatch: {report_json}"
                    )
                for metric, expected_value in expected_section.items():
                    _numeric_close(
                        actual_section.get(metric),
                        float(expected_value),
                        f"fgsm[{model_name}][{eps}].report.{section_name}.{metric}",
                    )
            else:
                _numeric_close(
                    actual_section,
                    float(expected_section),
                    f"fgsm[{model_name}][{eps}].report.{section_name}",
                )

        matrix_path = provisional_dir / f"fgsm_{model_name}_eps_{eps_str}_confusion_matrix.csv"
        if not matrix_path.is_file():
            raise AuditError(f"FGSM confusion matrix CSV missing: {matrix_path}")
        try:
            actual_matrix = pd.read_csv(matrix_path, header=None).to_numpy(dtype=float)
        except Exception as exc:
            raise AuditError(
                f"Failed to parse FGSM confusion matrix CSV: {matrix_path}",
                {"error": str(exc)},
            ) from exc
        expected_matrix = confusion_matrix(
            true_labels, adversarial_predictions, labels=class_names
        )
        if (
            actual_matrix.shape != expected_matrix.shape
            or not np.isfinite(actual_matrix).all()
            or not np.array_equal(actual_matrix, expected_matrix)
        ):
            raise AuditError(
                f"FGSM confusion matrix disagrees with sample evidence: {matrix_path}"
            )

        summary_row = summary_frame.iloc[EXPECTED_EPSILONS.index(eps)]
        expected_summary = {
            "test_samples": float(EXPECTED_TEST_SAMPLES),
            "clean_accuracy": float(clean_correct_count / EXPECTED_TEST_SAMPLES),
            "robust_accuracy": robust_accuracy,
            "accuracy_drop": float(
                clean_correct_count / EXPECTED_TEST_SAMPLES - robust_accuracy
            ),
            "macro_f1": float(
                f1_score(
                    true_labels,
                    adversarial_predictions,
                    labels=class_names,
                    average="macro",
                    zero_division=0,
                )
            ),
            "untargeted_asr": calculated_asr,
            "attack_successes": float(attack_success_count),
            "asr_denominator_clean_correct": float(clean_correct_count),
            "linf_max": max_linf,
            "linf_mean": mean_linf,
        }
        for field, expected_value in expected_summary.items():
            _numeric_close(
                summary_row[field],
                expected_value,
                f"fgsm[{model_name}][{eps}].summary.{field}",
                tolerance=5e-10 if field in {"linf_max", "linf_mean"} else 1e-12,
            )

        audited_epsilons[eps] = {
            "robust_accuracy": robust_accuracy,
            "attack_successes": attack_success_count,
            "asr_denominator": clean_correct_count,
            "untargeted_asr": calculated_asr,
            "max_linf": max_linf,
        }

    return audited_epsilons
