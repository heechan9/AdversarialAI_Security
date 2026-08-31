"""Audit provisional FGSM attack results, sample CSVs, report JSONs, and attack contract compliance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from adversarial_ai.audit.exceptions import AuditError

EXPECTED_TEST_SAMPLES = 781
EXPECTED_EPSILONS = [0.0, 0.01, 0.03, 0.05]


def audit_fgsm_results(
    provisional_dir: Path,
    model_name: str,
    clean_correct_count: int,
    clean_correct_mask: list[bool] | None = None,
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

    audited_epsilons: dict[float, dict[str, Any]] = {}

    for eps in EXPECTED_EPSILONS:
        # Check integer/float formatting in filename
        eps_str = "0" if eps == 0.0 else str(eps)
        sample_csv = provisional_dir / f"fgsm_{model_name}_eps_{eps_str}_samples.csv"
        report_json = provisional_dir / f"fgsm_{model_name}_eps_{eps_str}_report.json"

        if not sample_csv.is_file():
            raise AuditError(f"FGSM sample CSV missing for {model_name} eps={eps}: {sample_csv}")

        try:
            df = pd.read_csv(sample_csv)
        except Exception as exc:
            raise AuditError(f"Failed to read FGSM sample CSV: {sample_csv}", {"error": str(exc)}) from exc

        required_cols = {
            "relative_path",
            "epsilon",
            "true_label",
            "clean_predicted_label",
            "adversarial_predicted_label",
            "clean_correct",
            "attack_success",
            "linf",
        }
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise AuditError(
                f"FGSM sample CSV missing required columns: {sorted(missing_cols)} in {sample_csv}"
            )

        if len(df) != EXPECTED_TEST_SAMPLES:
            raise AuditError(
                f"FGSM sample CSV row count for {model_name} eps={eps} must be {EXPECTED_TEST_SAMPLES}, got {len(df)}",
                {"expected": EXPECTED_TEST_SAMPLES, "actual": len(df)},
            )

        # Cross-check clean_correct mask if provided
        if clean_correct_mask is not None:
            csv_clean_correct = df["clean_correct"].astype(bool).tolist()
            if csv_clean_correct != clean_correct_mask:
                diff_count = sum(c1 != c2 for c1, c2 in zip(csv_clean_correct, clean_correct_mask))
                raise AuditError(
                    f"FGSM sample CSV clean_correct column disagrees with clean baseline eval CSV for {model_name} eps={eps} across {diff_count} samples",
                    {"diff_count": diff_count, "model": model_name, "epsilon": eps},
                )

        # Derived calculations
        clean_correct_derived = df["clean_correct"].astype(bool)
        actual_clean_correct_count = int(clean_correct_derived.sum())

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
        adv_correct_derived = df["true_label"] == df["adversarial_predicted_label"]
        computed_attack_success = clean_correct_derived & (~adv_correct_derived)
        csv_attack_success = df["attack_success"].astype(bool)

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
        linf_values = df["linf"].astype(float)
        max_linf = float(linf_values.max())

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

        # Report JSON cross-verification
        if report_json.is_file():
            try:
                report = json.loads(report_json.read_text(encoding="utf-8"))
            except Exception as exc:
                raise AuditError(f"Failed to read report JSON: {report_json}", {"error": str(exc)}) from exc

            rep_robust_acc = report.get("robust_accuracy")
            rep_asr = report.get("untargeted_asr")
            rep_successes = report.get("attack_successes")
            rep_denom = report.get("asr_denominator") or report.get("clean_correct")

            if rep_robust_acc is not None and abs(rep_robust_acc - robust_accuracy) > 1e-6:
                raise AuditError(
                    f"Report JSON robust_accuracy ({rep_robust_acc}) disagrees with recalculated CSV ({robust_accuracy})",
                    {"report_acc": rep_robust_acc, "recalculated_acc": robust_accuracy},
                )

            if rep_asr is not None and abs(rep_asr - calculated_asr) > 1e-6:
                raise AuditError(
                    f"Report JSON ASR ({rep_asr}) disagrees with recalculated CSV ({calculated_asr})",
                    {"report_asr": rep_asr, "recalculated_asr": calculated_asr},
                )

            if rep_successes is not None and rep_successes != attack_success_count:
                raise AuditError(
                    f"Report JSON attack_successes ({rep_successes}) disagrees with recalculated CSV ({attack_success_count})",
                    {"report_successes": rep_successes, "recalculated_successes": attack_success_count},
                )

            if rep_denom is not None and rep_denom != clean_correct_count:
                raise AuditError(
                    f"Report JSON ASR denominator ({rep_denom}) disagrees with clean-correct expectation ({clean_correct_count})",
                    {"report_denom": rep_denom, "clean_correct_count": clean_correct_count},
                )

        audited_epsilons[eps] = {
            "robust_accuracy": robust_accuracy,
            "attack_successes": attack_success_count,
            "asr_denominator": clean_correct_count,
            "untargeted_asr": calculated_asr,
            "max_linf": max_linf,
        }

    return audited_epsilons
