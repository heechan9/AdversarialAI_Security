"""Stage A: independently recompute committed Clean evaluation metrics.

Scope (narrowed after review of PR #20 against ``main``):

1. Probability-column integrity of ``results/clean/<model>_eval.csv`` --- every
   probability is finite and within ``[0, 1]``, each row sums to 1, and the
   argmax of the probability columns agrees with ``predicted_index`` /
   ``predicted_label``.
2. Independent recomputation of the Clean classification report
   (``<model>_report.json`` and ``<model>_report.csv``) and the Clean confusion
   matrix (``<model>_confusion_matrix.csv``) from the per-sample rows.

Everything else the repository audit already recalculates dynamically --- clean
correct count and accuracy, FGSM robust accuracy / ASR / ASR denominator, the
L-infinity contract, the eps=0 control, FGSM macro F1, the FGSM confusion
matrices, ``linf_mean``, the ``fgsm_<model>.csv`` summary rows and the
Clean-to-FGSM path and row-order agreement --- is out of scope here and is not
duplicated.

Independence rules for this module:

* It imports nothing from ``adversarial_ai``.
* It uses the Python standard library only --- no pandas, no numpy, no
  scikit-learn. The metric definitions are reimplemented from scratch so that a
  shared library bug cannot hide behind itself.
* It never writes to ``results/clean/``, ``results/attacks/`` or ``configs/``.
  Findings are reported; committed evidence is left exactly as it is.

The harness is fail-closed: a missing file, an unparsable value or a check that
cannot be carried out is a failure, never a skip.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

# --- Tolerances -------------------------------------------------------------
#
# Probabilities are serialized from float32 tensors, so their row sums carry
# float32-scale error. The report and confusion matrix, by contrast, are pure
# float64 functions of the committed labels, so they are held to a far tighter
# bound. ``test_accuracy`` in the summary JSON comes from a float32 Keras
# evaluate() call and is the one summary field that needs the loose bound.

PROBABILITY_SUM_TOLERANCE = 1e-5
PROBABILITY_RANGE_TOLERANCE = 1e-6
REPORT_METRIC_TOLERANCE = 1e-9
FLOAT32_SUMMARY_TOLERANCE = 1e-6

PROBABILITY_COLUMN_PATTERN = re.compile(r"^prob_(\d+)_(.+)$")

REQUIRED_EVAL_COLUMNS = (
    "relative_path",
    "true_index",
    "true_label",
    "predicted_index",
    "predicted_label",
)

REPORT_METRIC_KEYS = ("precision", "recall", "f1-score", "support")


class VerificationError(Exception):
    """Raised when committed evidence cannot be read or parsed at all."""


@dataclass
class Check:
    """One independently recomputed assertion about committed evidence."""

    name: str
    passed: bool
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": "PASS" if self.passed else "FAIL",
            "detail": self.detail,
            "evidence": self.evidence,
        }


@dataclass
class CleanEvalTable:
    """Parsed per-sample Clean evaluation CSV."""

    path: Path
    relative_paths: list[str]
    true_indices: list[int]
    true_labels: list[str]
    predicted_indices: list[int]
    predicted_labels: list[str]
    probabilities: list[list[float]]
    probability_classes: list[str]

    @property
    def row_count(self) -> int:
        return len(self.relative_paths)


# --- Parsing ----------------------------------------------------------------


def load_classes(classes_json_path: Path) -> list[str]:
    """Return class labels ordered by their integer index in ``classes.json``."""
    payload = _read_json(classes_json_path)
    if not isinstance(payload, dict) or not payload:
        raise VerificationError(f"Class map must be a non-empty object: {classes_json_path}")

    indexed: dict[int, str] = {}
    for raw_index, label in payload.items():
        try:
            index = int(raw_index)
        except (TypeError, ValueError) as exc:
            raise VerificationError(
                f"Class map key is not an integer index: {raw_index!r} in {classes_json_path}"
            ) from exc
        if not isinstance(label, str) or not label.strip():
            raise VerificationError(
                f"Class map label for index {index} is empty in {classes_json_path}"
            )
        if index in indexed:
            raise VerificationError(f"Duplicate class index {index} in {classes_json_path}")
        indexed[index] = label

    if sorted(indexed) != list(range(len(indexed))):
        raise VerificationError(
            f"Class map indices must be contiguous from 0: got {sorted(indexed)} "
            f"in {classes_json_path}"
        )
    return [indexed[index] for index in range(len(indexed))]


def read_clean_eval_csv(eval_csv_path: Path, classes: Sequence[str]) -> CleanEvalTable:
    """Parse a Clean per-sample CSV with the standard library only."""
    rows, fieldnames = _read_csv_rows(eval_csv_path)
    if not rows:
        raise VerificationError(f"Clean evaluation CSV has no data rows: {eval_csv_path}")

    missing = [column for column in REQUIRED_EVAL_COLUMNS if column not in fieldnames]
    if missing:
        raise VerificationError(
            f"Clean evaluation CSV missing required columns {missing}: {eval_csv_path}"
        )

    probability_columns = _resolve_probability_columns(fieldnames, classes, eval_csv_path)

    relative_paths: list[str] = []
    true_indices: list[int] = []
    true_labels: list[str] = []
    predicted_indices: list[int] = []
    predicted_labels: list[str] = []
    probabilities: list[list[float]] = []

    for row_number, row in enumerate(rows):
        where = f"{eval_csv_path.name}[row {row_number}]"
        relative_paths.append(_require_text(row["relative_path"], f"{where}.relative_path"))
        true_indices.append(_require_index(row["true_index"], len(classes), f"{where}.true_index"))
        true_labels.append(_require_text(row["true_label"], f"{where}.true_label"))
        predicted_indices.append(
            _require_index(row["predicted_index"], len(classes), f"{where}.predicted_index")
        )
        predicted_labels.append(_require_text(row["predicted_label"], f"{where}.predicted_label"))
        probabilities.append(
            [_require_float(row[column], f"{where}.{column}") for column in probability_columns]
        )

    return CleanEvalTable(
        path=eval_csv_path,
        relative_paths=relative_paths,
        true_indices=true_indices,
        true_labels=true_labels,
        predicted_indices=predicted_indices,
        predicted_labels=predicted_labels,
        probabilities=probabilities,
        probability_classes=list(classes),
    )


def _resolve_probability_columns(
    fieldnames: Sequence[str], classes: Sequence[str], eval_csv_path: Path
) -> list[str]:
    """Return the ``prob_<index>_<label>`` columns ordered by class index."""
    by_index: dict[int, str] = {}
    for column in fieldnames:
        match = PROBABILITY_COLUMN_PATTERN.match(column)
        if match is None:
            continue
        index = int(match.group(1))
        label = match.group(2)
        if index >= len(classes):
            raise VerificationError(
                f"Probability column {column!r} has index {index} outside the class map "
                f"of size {len(classes)}: {eval_csv_path}"
            )
        if classes[index] != label:
            raise VerificationError(
                f"Probability column {column!r} names {label!r} but the class map has "
                f"{classes[index]!r} at index {index}: {eval_csv_path}"
            )
        if index in by_index:
            raise VerificationError(
                f"Duplicate probability column for class index {index}: {eval_csv_path}"
            )
        by_index[index] = column

    if sorted(by_index) != list(range(len(classes))):
        raise VerificationError(
            f"Clean evaluation CSV must carry one probability column per class "
            f"(expected {len(classes)}, found indices {sorted(by_index)}): {eval_csv_path}"
        )
    return [by_index[index] for index in range(len(classes))]


# --- Check group 1: probability columns -------------------------------------


def check_probability_columns(table: CleanEvalTable) -> list[Check]:
    """Verify finiteness, range, row sums and argmax agreement of probabilities."""
    non_finite: list[dict[str, Any]] = []
    out_of_range: list[dict[str, Any]] = []
    bad_sums: list[dict[str, Any]] = []
    argmax_mismatches: list[dict[str, Any]] = []
    argmax_ties: list[dict[str, Any]] = []
    label_mismatches: list[dict[str, Any]] = []

    worst_sum_error = 0.0

    for row_number, probabilities in enumerate(table.probabilities):
        location = {"row": row_number, "relative_path": table.relative_paths[row_number]}

        row_finite = True
        for class_index, value in enumerate(probabilities):
            if not math.isfinite(value):
                row_finite = False
                non_finite.append({**location, "class_index": class_index, "value": repr(value)})
            elif value < -PROBABILITY_RANGE_TOLERANCE or value > 1.0 + PROBABILITY_RANGE_TOLERANCE:
                out_of_range.append({**location, "class_index": class_index, "value": value})

        if not row_finite:
            # A row carrying NaN/inf cannot yield a meaningful sum or argmax. It
            # is already reported above and must not be silently passed here.
            continue

        total = math.fsum(probabilities)
        sum_error = abs(total - 1.0)
        worst_sum_error = max(worst_sum_error, sum_error)
        if sum_error > PROBABILITY_SUM_TOLERANCE:
            bad_sums.append({**location, "sum": total, "abs_error": sum_error})

        highest = max(probabilities)
        tied = [index for index, value in enumerate(probabilities) if value == highest]
        declared_index = table.predicted_indices[row_number]

        if len(tied) > 1:
            # A tie makes predicted_index unverifiable from the probabilities,
            # so it is reported rather than resolved by a tie-break convention.
            argmax_ties.append({**location, "tied_class_indices": tied, "value": highest})
        elif tied[0] != declared_index:
            argmax_mismatches.append(
                {
                    **location,
                    "argmax_index": tied[0],
                    "declared_predicted_index": declared_index,
                    "argmax_probability": highest,
                    "declared_probability": probabilities[declared_index],
                }
            )

        expected_label = table.probability_classes[declared_index]
        if table.predicted_labels[row_number] != expected_label:
            label_mismatches.append(
                {
                    **location,
                    "declared_predicted_index": declared_index,
                    "declared_predicted_label": table.predicted_labels[row_number],
                    "class_map_label": expected_label,
                }
            )

    true_label_mismatches = [
        {
            "row": row_number,
            "relative_path": table.relative_paths[row_number],
            "true_index": true_index,
            "true_label": table.true_labels[row_number],
            "class_map_label": table.probability_classes[true_index],
        }
        for row_number, true_index in enumerate(table.true_indices)
        if table.true_labels[row_number] != table.probability_classes[true_index]
    ]

    return [
        _sample_check(
            "clean.probabilities.finite",
            non_finite,
            f"All {table.row_count} rows carry finite probabilities",
            "rows with a non-finite probability",
        ),
        _sample_check(
            "clean.probabilities.range",
            out_of_range,
            f"All probabilities lie within [0, 1] (+/- {PROBABILITY_RANGE_TOLERANCE:g})",
            "probabilities outside [0, 1]",
        ),
        _sample_check(
            "clean.probabilities.row_sum",
            bad_sums,
            f"All {table.row_count} probability rows sum to 1 (worst |sum - 1| = "
            f"{worst_sum_error:.3e}, tolerance {PROBABILITY_SUM_TOLERANCE:g})",
            "rows whose probabilities do not sum to 1",
            evidence={"worst_abs_error": worst_sum_error},
        ),
        _sample_check(
            "clean.probabilities.argmax_unique",
            argmax_ties,
            "Every row has a single strict argmax",
            "rows with a tied argmax, leaving predicted_index unverifiable",
        ),
        _sample_check(
            "clean.probabilities.argmax_matches_predicted_index",
            argmax_mismatches,
            f"Probability argmax agrees with predicted_index on all {table.row_count} rows",
            "rows where the probability argmax disagrees with predicted_index",
        ),
        _sample_check(
            "clean.predicted_index_matches_predicted_label",
            label_mismatches,
            "predicted_index and predicted_label agree with the class map on all rows",
            "rows where predicted_label disagrees with the class map",
        ),
        _sample_check(
            "clean.true_index_matches_true_label",
            true_label_mismatches,
            "true_index and true_label agree with the class map on all rows",
            "rows where true_label disagrees with the class map",
        ),
    ]


# --- Check group 2: classification report and confusion matrix ---------------


def recompute_confusion_matrix(
    true_labels: Sequence[str], predicted_labels: Sequence[str], classes: Sequence[str]
) -> list[list[int]]:
    """Return ``matrix[true][predicted]`` counts, reimplemented from scratch."""
    position = {label: index for index, label in enumerate(classes)}
    matrix = [[0] * len(classes) for _ in classes]
    for row_number, (true_label, predicted_label) in enumerate(zip(true_labels, predicted_labels)):
        if true_label not in position:
            raise VerificationError(f"Unknown true_label {true_label!r} at row {row_number}")
        if predicted_label not in position:
            raise VerificationError(
                f"Unknown predicted_label {predicted_label!r} at row {row_number}"
            )
        matrix[position[true_label]][position[predicted_label]] += 1
    return matrix


def recompute_classification_report(
    true_labels: Sequence[str], predicted_labels: Sequence[str], classes: Sequence[str]
) -> dict[str, Any]:
    """Recompute a scikit-learn-shaped classification report without scikit-learn.

    Precision, recall and F1 are defined directly from the confusion matrix. A
    class with no predictions gets precision 0 and a class with no support gets
    recall 0, matching the ``zero_division=0`` convention the committed reports
    were produced under.
    """
    matrix = recompute_confusion_matrix(true_labels, predicted_labels, classes)
    total = len(true_labels)
    if total == 0:
        raise VerificationError("Cannot recompute a classification report from zero rows")

    per_class: dict[str, dict[str, float]] = {}
    for index, label in enumerate(classes):
        true_positive = matrix[index][index]
        support = sum(matrix[index])
        predicted_positive = sum(matrix[row][index] for row in range(len(classes)))

        precision = true_positive / predicted_positive if predicted_positive else 0.0
        recall = true_positive / support if support else 0.0
        f1 = (
            2.0 * precision * recall / (precision + recall) if (precision + recall) > 0.0 else 0.0
        )
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1-score": f1,
            "support": float(support),
        }

    correct = sum(matrix[index][index] for index in range(len(classes)))

    report: dict[str, Any] = dict(per_class)
    report["accuracy"] = correct / total
    report["macro avg"] = {
        metric: _mean([per_class[label][metric] for label in classes])
        for metric in ("precision", "recall", "f1-score")
    }
    report["macro avg"]["support"] = float(total)

    weights = [per_class[label]["support"] for label in classes]
    report["weighted avg"] = {
        metric: _weighted_mean([per_class[label][metric] for label in classes], weights)
        for metric in ("precision", "recall", "f1-score")
    }
    report["weighted avg"]["support"] = float(total)
    return report


def check_confusion_matrix(
    matrix_csv_path: Path, recomputed: Sequence[Sequence[int]]
) -> list[Check]:
    """Compare the committed confusion matrix CSV against the recomputed one."""
    committed = _read_integer_matrix(matrix_csv_path)

    if len(committed) != len(recomputed) or any(len(row) != len(recomputed) for row in committed):
        return [
            Check(
                name="clean.confusion_matrix.shape",
                passed=False,
                detail=(
                    f"Committed confusion matrix shape disagrees with the recomputed "
                    f"{len(recomputed)}x{len(recomputed)} matrix: {matrix_csv_path}"
                ),
                evidence={
                    "committed_rows": len(committed),
                    "committed_row_widths": sorted({len(row) for row in committed}),
                    "expected_size": len(recomputed),
                },
            )
        ]

    differences = [
        {
            "true_index": row,
            "predicted_index": column,
            "committed": committed[row][column],
            "recomputed": recomputed[row][column],
        }
        for row in range(len(recomputed))
        for column in range(len(recomputed))
        if committed[row][column] != recomputed[row][column]
    ]

    return [
        Check(
            name="clean.confusion_matrix.shape",
            passed=True,
            detail=f"Committed confusion matrix is {len(recomputed)}x{len(recomputed)} as recomputed",
        ),
        _sample_check(
            "clean.confusion_matrix.cells",
            differences,
            f"All {len(recomputed) ** 2} confusion matrix cells match the independent "
            "recomputation",
            "confusion matrix cells that disagree",
        ),
    ]


def check_report_json(report_json_path: Path, recomputed: dict[str, Any]) -> list[Check]:
    """Compare the committed report JSON against the recomputed report."""
    committed = _read_json(report_json_path)
    if not isinstance(committed, dict):
        raise VerificationError(f"Clean report JSON root must be an object: {report_json_path}")

    if set(committed) != set(recomputed):
        return [
            Check(
                name="clean.report_json.keys",
                passed=False,
                detail=(
                    f"Committed report JSON keys disagree with the recomputation: "
                    f"{report_json_path}"
                ),
                evidence={
                    "only_in_committed": sorted(set(committed) - set(recomputed)),
                    "only_in_recomputed": sorted(set(recomputed) - set(committed)),
                },
            )
        ]

    differences: list[dict[str, Any]] = []
    for section, expected in recomputed.items():
        actual = committed[section]
        if isinstance(expected, dict):
            if not isinstance(actual, dict) or set(actual) != set(expected):
                differences.append({"section": section, "reason": "schema mismatch"})
                continue
            for metric, expected_value in expected.items():
                difference = _float_difference(actual[metric], expected_value)
                if difference is None or difference > REPORT_METRIC_TOLERANCE:
                    differences.append(
                        {
                            "section": section,
                            "metric": metric,
                            "committed": actual[metric],
                            "recomputed": expected_value,
                            "abs_difference": difference,
                        }
                    )
        else:
            difference = _float_difference(actual, expected)
            if difference is None or difference > REPORT_METRIC_TOLERANCE:
                differences.append(
                    {
                        "section": section,
                        "committed": actual,
                        "recomputed": expected,
                        "abs_difference": difference,
                    }
                )

    return [
        Check(
            name="clean.report_json.keys",
            passed=True,
            detail=(
                f"Committed report JSON carries exactly the {len(recomputed)} recomputed sections"
            ),
        ),
        _sample_check(
            "clean.report_json.values",
            differences,
            f"Every committed report JSON value matches the independent recomputation "
            f"(tolerance {REPORT_METRIC_TOLERANCE:g})",
            "report JSON values that disagree",
        ),
    ]


def check_report_csv(report_csv_path: Path, recomputed: dict[str, Any]) -> list[Check]:
    """Compare the committed report CSV against the recomputed report.

    The CSV carries the same numbers as the JSON in a flat table, including the
    ``accuracy`` row where the exporter repeats the scalar accuracy across all
    four metric columns.
    """
    rows, fieldnames = _read_csv_rows(report_csv_path)
    if not rows:
        raise VerificationError(f"Clean report CSV has no data rows: {report_csv_path}")

    label_column = fieldnames[0]
    missing_metrics = [key for key in REPORT_METRIC_KEYS if key not in fieldnames]
    if missing_metrics:
        raise VerificationError(
            f"Clean report CSV missing metric columns {missing_metrics}: {report_csv_path}"
        )

    committed: dict[str, dict[str, str]] = {}
    for row in rows:
        section = (row.get(label_column) or "").strip()
        if not section:
            raise VerificationError(f"Clean report CSV has an unnamed row: {report_csv_path}")
        if section in committed:
            raise VerificationError(
                f"Clean report CSV repeats section {section!r}: {report_csv_path}"
            )
        committed[section] = row

    if set(committed) != set(recomputed):
        return [
            Check(
                name="clean.report_csv.sections",
                passed=False,
                detail=(
                    f"Committed report CSV sections disagree with the recomputation: "
                    f"{report_csv_path}"
                ),
                evidence={
                    "only_in_committed": sorted(set(committed) - set(recomputed)),
                    "only_in_recomputed": sorted(set(recomputed) - set(committed)),
                },
            )
        ]

    differences: list[dict[str, Any]] = []
    for section, expected in recomputed.items():
        row = committed[section]
        for metric in REPORT_METRIC_KEYS:
            # The exporter repeats the scalar accuracy in every column of the
            # ``accuracy`` row, so a non-dict section compares against itself.
            expected_value = expected[metric] if isinstance(expected, dict) else expected
            try:
                actual_value = float(row[metric])
            except (TypeError, ValueError):
                differences.append(
                    {
                        "section": section,
                        "metric": metric,
                        "committed": row[metric],
                        "reason": "not a float",
                    }
                )
                continue
            difference = _float_difference(actual_value, expected_value)
            if difference is None or difference > REPORT_METRIC_TOLERANCE:
                differences.append(
                    {
                        "section": section,
                        "metric": metric,
                        "committed": actual_value,
                        "recomputed": expected_value,
                        "abs_difference": difference,
                    }
                )

    return [
        Check(
            name="clean.report_csv.sections",
            passed=True,
            detail=(
                f"Committed report CSV carries exactly the {len(recomputed)} recomputed sections"
            ),
        ),
        _sample_check(
            "clean.report_csv.values",
            differences,
            f"Every committed report CSV value matches the independent recomputation "
            f"(tolerance {REPORT_METRIC_TOLERANCE:g})",
            "report CSV values that disagree",
        ),
    ]


def check_summary_json(
    summary_json_path: Path, recomputed: dict[str, Any], row_count: int
) -> list[Check]:
    """Cross-check the summary JSON headline metrics against the recomputation.

    ``macro_f1`` and ``weighted_f1`` are float64 functions of the committed
    labels and are held to the tight tolerance. ``test_accuracy`` is read back
    from a float32 Keras evaluate() call, so it only has to agree to
    ``FLOAT32_SUMMARY_TOLERANCE``.
    """
    committed = _read_json(summary_json_path)
    if not isinstance(committed, dict):
        raise VerificationError(f"Clean summary JSON root must be an object: {summary_json_path}")

    expected_correct = round(recomputed["accuracy"] * row_count)
    comparisons = [
        ("test_samples", float(row_count), 0.0),
        ("correct_predictions", float(expected_correct), 0.0),
        ("macro_f1", recomputed["macro avg"]["f1-score"], REPORT_METRIC_TOLERANCE),
        ("weighted_f1", recomputed["weighted avg"]["f1-score"], REPORT_METRIC_TOLERANCE),
        ("test_accuracy", recomputed["accuracy"], FLOAT32_SUMMARY_TOLERANCE),
    ]

    differences: list[dict[str, Any]] = []
    for field_name, expected_value, tolerance in comparisons:
        if field_name not in committed:
            differences.append({"field": field_name, "reason": "missing from summary JSON"})
            continue
        difference = _float_difference(committed[field_name], expected_value)
        if difference is None or difference > tolerance:
            differences.append(
                {
                    "field": field_name,
                    "committed": committed[field_name],
                    "recomputed": expected_value,
                    "abs_difference": difference,
                    "tolerance": tolerance,
                }
            )

    return [
        _sample_check(
            "clean.summary_json.headline_metrics",
            differences,
            f"All {len(comparisons)} summary JSON headline metrics match the independent "
            "recomputation",
            "summary JSON metrics that disagree",
        )
    ]


# --- Orchestration ----------------------------------------------------------


def load_declared_models(experiment_yaml_path: Path) -> list[str]:
    """Read the model roster from the ``models:`` block of ``experiment.yaml``.

    The roster is read from the config rather than from whichever result files
    happen to exist, so deleting evidence cannot quietly shrink the verified
    set. This is a narrow scan of one known block, not a general YAML parser ---
    the harness stays on the standard library, and anything it cannot read is a
    failure rather than an empty roster.
    """
    if not experiment_yaml_path.is_file():
        raise VerificationError(f"Required file missing: {experiment_yaml_path}")
    try:
        lines = experiment_yaml_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise VerificationError(f"Failed to read {experiment_yaml_path}: {exc}") from exc

    names: list[str] = []
    child_indent: int | None = None
    in_block = False
    for raw_line in lines:
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())

        if not in_block:
            if indent == 0 and line.strip() == "models:":
                in_block = True
            continue

        if indent == 0:
            break  # the models block ended
        if child_indent is None:
            child_indent = indent
        if indent == child_indent:
            key = line.strip()
            if not key.endswith(":"):
                raise VerificationError(
                    f"Unexpected entry in the models block of {experiment_yaml_path}: {key!r}"
                )
            name = key[:-1].strip()
            if not name:
                raise VerificationError(f"Empty model name in {experiment_yaml_path}")
            if name in names:
                raise VerificationError(f"Duplicate model {name!r} in {experiment_yaml_path}")
            names.append(name)

    if not in_block:
        raise VerificationError(f"No 'models:' block found in {experiment_yaml_path}")
    if not names:
        raise VerificationError(f"The 'models:' block of {experiment_yaml_path} is empty")
    return sorted(names)


def discover_clean_models(clean_dir: Path) -> list[str]:
    """Return model names implied by the Clean artefacts present on disk.

    The union of every artefact family is used --- not just ``*_eval.csv`` --- so
    that a model whose per-sample CSV was removed still shows up and is failed by
    the per-model checks rather than silently dropped.
    """
    if not clean_dir.is_dir():
        raise VerificationError(f"Clean results directory missing: {clean_dir}")
    suffixes = (
        "_eval.csv",
        "_report.json",
        "_report.csv",
        "_confusion_matrix.csv",
        "_summary.json",
    )
    names = {
        path.name[: -len(suffix)]
        for suffix in suffixes
        for path in clean_dir.glob(f"*{suffix}")
    }
    return sorted(names)


def verify_model(repo_root: Path, model_name: str, classes: Sequence[str]) -> dict[str, Any]:
    """Run every Stage A check for one model, fail-closed."""
    clean_dir = repo_root / "results" / "clean"
    inputs = {
        "eval_csv": clean_dir / f"{model_name}_eval.csv",
        "report_json": clean_dir / f"{model_name}_report.json",
        "report_csv": clean_dir / f"{model_name}_report.csv",
        "confusion_matrix_csv": clean_dir / f"{model_name}_confusion_matrix.csv",
        "summary_json": clean_dir / f"{model_name}_summary.json",
    }

    checks: list[Check] = []
    row_count: int | None = None
    try:
        table = read_clean_eval_csv(inputs["eval_csv"], classes)
        row_count = table.row_count
        checks.extend(check_probability_columns(table))

        recomputed_report = recompute_classification_report(
            table.true_labels, table.predicted_labels, classes
        )
        recomputed_matrix = recompute_confusion_matrix(
            table.true_labels, table.predicted_labels, classes
        )

        checks.extend(check_confusion_matrix(inputs["confusion_matrix_csv"], recomputed_matrix))
        checks.extend(check_report_json(inputs["report_json"], recomputed_report))
        checks.extend(check_report_csv(inputs["report_csv"], recomputed_report))
        checks.extend(check_summary_json(inputs["summary_json"], recomputed_report, row_count))
    except VerificationError as exc:
        # Fail closed: evidence that cannot be read or parsed is a failure, not
        # a skipped check.
        checks.append(
            Check(
                name="clean.evidence.readable",
                passed=False,
                detail=f"Could not complete Stage A for {model_name}: {exc}",
            )
        )

    return {
        "model": model_name,
        "row_count": row_count,
        "inputs": {key: _relative_to(path, repo_root) for key, path in inputs.items()},
        "checks": [check.to_dict() for check in checks],
        "failed_checks": sum(1 for check in checks if not check.passed),
        "status": "PASS" if checks and all(check.passed for check in checks) else "FAIL",
    }


def run_stage_a(repo_root: Path) -> dict[str, Any]:
    """Run Stage A across every discovered Clean model."""
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    base: dict[str, Any] = {
        "stage": "A",
        "scope": "clean probability columns, classification report, confusion matrix",
        "generated_at_utc": generated_at,
        # The verified commit identifies the evidence; the checkout path does
        # not, and would only pin this artefact to one machine.
        "verified_commit": _read_git_commit(repo_root),
        "imports_repository_code": False,
        "third_party_dependencies": [],
    }

    try:
        classes = load_classes(repo_root / "configs" / "classes.json")
        declared = load_declared_models(repo_root / "configs" / "experiment.yaml")
        present = discover_clean_models(repo_root / "results" / "clean")
    except VerificationError as exc:
        return {**base, "status": "FAIL", "models": [], "failure": str(exc)}

    # Verify every declared model, so a deleted result file fails the run
    # instead of shrinking it. Undeclared artefacts are a failure too: they mean
    # the config and the results directory disagree about what was evaluated.
    roster_failure = None
    if present != declared:
        roster_failure = {
            "declared_in_experiment_yaml": declared,
            "present_in_results_clean": present,
            "declared_but_missing": sorted(set(declared) - set(present)),
            "present_but_undeclared": sorted(set(present) - set(declared)),
        }

    models = [verify_model(repo_root, model_name, classes) for model_name in sorted(declared)]
    models_passed = bool(models) and all(m["status"] == "PASS" for m in models)
    return {
        **base,
        "classes": list(classes),
        "declared_models": declared,
        **({"roster_mismatch": roster_failure} if roster_failure else {}),
        "tolerances": {
            "probability_row_sum": PROBABILITY_SUM_TOLERANCE,
            "probability_range": PROBABILITY_RANGE_TOLERANCE,
            "report_metric": REPORT_METRIC_TOLERANCE,
            "float32_summary": FLOAT32_SUMMARY_TOLERANCE,
        },
        "models": models,
        "status": "PASS" if models_passed and roster_failure is None else "FAIL",
    }


# --- Small helpers ----------------------------------------------------------


def _sample_check(
    name: str,
    offenders: Sequence[dict[str, Any]],
    pass_detail: str,
    failure_noun: str,
    evidence: dict[str, Any] | None = None,
    sample_size: int = 5,
) -> Check:
    """Build a Check from offending records, keeping a bounded sample as evidence."""
    base = dict(evidence or {})
    if not offenders:
        return Check(name=name, passed=True, detail=pass_detail, evidence=base)
    base.update({"offending_count": len(offenders), "sample": list(offenders[:sample_size])})
    return Check(
        name=name,
        passed=False,
        detail=f"Found {len(offenders)} {failure_noun}",
        evidence=base,
    )


def _float_difference(actual: Any, expected: float) -> float | None:
    """Return ``|actual - expected|``, or None when ``actual`` is not a finite number."""
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return None
    value = float(actual)
    if not math.isfinite(value):
        return None
    return abs(value - expected)


def _mean(values: Sequence[float]) -> float:
    return math.fsum(values) / len(values)


def _weighted_mean(values: Sequence[float], weights: Sequence[float]) -> float:
    total_weight = math.fsum(weights)
    if total_weight == 0.0:
        return 0.0
    return math.fsum(value * weight for value, weight in zip(values, weights)) / total_weight


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise VerificationError(f"Required file missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"Failed to read JSON {path}: {exc}") from exc


def _read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    if not path.is_file():
        raise VerificationError(f"Required file missing: {path}")
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
    except OSError as exc:
        raise VerificationError(f"Failed to read CSV {path}: {exc}") from exc
    if not fieldnames:
        raise VerificationError(f"CSV has no header row: {path}")
    for row_number, row in enumerate(rows):
        if None in row or any(value is None for value in row.values()):
            raise VerificationError(
                f"CSV row {row_number} has a different column count than the header: {path}"
            )
    return rows, fieldnames


def _read_integer_matrix(path: Path) -> list[list[int]]:
    """Read a headerless square integer matrix CSV."""
    if not path.is_file():
        raise VerificationError(f"Required file missing: {path}")
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            raw_rows = [
                row for row in csv.reader(handle) if row and any(cell.strip() for cell in row)
            ]
    except OSError as exc:
        raise VerificationError(f"Failed to read CSV {path}: {exc}") from exc
    if not raw_rows:
        raise VerificationError(f"Confusion matrix CSV is empty: {path}")

    matrix: list[list[int]] = []
    for row_number, raw_row in enumerate(raw_rows):
        parsed: list[int] = []
        for column_number, cell in enumerate(raw_row):
            text = cell.strip()
            try:
                value = int(text)
            except ValueError as exc:
                raise VerificationError(
                    f"Confusion matrix cell [{row_number}][{column_number}] is not an integer "
                    f"({text!r}): {path}"
                ) from exc
            if value < 0:
                raise VerificationError(
                    f"Confusion matrix cell [{row_number}][{column_number}] is negative: {path}"
                )
            parsed.append(value)
        matrix.append(parsed)
    return matrix


def _relative_to(path: Path, repo_root: Path) -> str:
    """Render a path relative to the checkout, with forward slashes."""
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _read_git_commit(repo_root: Path) -> str | None:
    """Read the checked-out commit from ``.git`` without shelling out.

    Returns None when the commit cannot be determined --- this is provenance
    metadata, not evidence, so its absence does not fail the run.
    """
    head_path = repo_root / ".git" / "HEAD"
    if not head_path.is_file():
        return None
    try:
        head = head_path.read_text(encoding="utf-8").strip()
        if not head.startswith("ref:"):
            return head or None
        ref = head.split(":", 1)[1].strip()
        ref_path = repo_root / ".git" / ref
        if ref_path.is_file():
            return ref_path.read_text(encoding="utf-8").strip() or None
        packed = repo_root / ".git" / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                if line.startswith("#") or " " not in line:
                    continue
                sha, name = line.split(" ", 1)
                if name.strip() == ref:
                    return sha
    except OSError:
        return None
    return None


def _require_text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VerificationError(f"Expected a non-empty string at {where}, got {value!r}")
    return value.strip()


def _require_index(value: Any, class_count: int, where: str) -> int:
    text = _require_text(value, where)
    try:
        index = int(text)
    except ValueError as exc:
        raise VerificationError(f"Expected an integer at {where}, got {text!r}") from exc
    if not 0 <= index < class_count:
        raise VerificationError(
            f"Index at {where} is outside the class map of size {class_count}: {index}"
        )
    return index


def _require_float(value: Any, where: str) -> float:
    text = _require_text(value, where)
    try:
        return float(text)
    except ValueError as exc:
        raise VerificationError(f"Expected a float at {where}, got {text!r}") from exc


def format_report(report: dict[str, Any]) -> str:
    """Render a human-readable summary of a Stage A report."""
    lines = [
        "Independent verification --- Stage A (Clean artefact recomputation)",
        f"  commit    : {report.get('verified_commit') or 'unknown'}",
        f"  generated : {report['generated_at_utc']}",
        "",
    ]
    if "failure" in report:
        lines.append(f"  [FAIL] {report['failure']}")
        lines.append("")
    if "roster_mismatch" in report:
        mismatch = report["roster_mismatch"]
        lines.append(
            "  [FAIL] results/clean disagrees with the experiment.yaml model roster: "
            f"declared-but-missing={mismatch['declared_but_missing']}, "
            f"present-but-undeclared={mismatch['present_but_undeclared']}"
        )
        lines.append("")
    for model in report.get("models", []):
        lines.append(f"  [{model['status']}] {model['model']} ({model['row_count']} rows)")
        for check in model["checks"]:
            lines.append(f"      [{check['status']}] {check['name']}: {check['detail']}")
        lines.append("")
    lines.append(f"OVERALL: {report['status']}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Independently recompute committed Clean evaluation metrics (Stage A)."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root holding configs/ and results/ (default: this checkout)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Where to write the JSON report (default: "
        "<repo-root>/results/verification/stage_a/clean_recompute_report.json)",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    report = run_stage_a(repo_root)

    output_path = args.output or (
        repo_root / "results" / "verification" / "stage_a" / "clean_recompute_report.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(format_report(report))
    print(f"Report written to {output_path}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
