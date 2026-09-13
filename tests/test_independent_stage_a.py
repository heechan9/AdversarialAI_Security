"""Mutation tests for the independent Stage A Clean recomputation harness.

Each test tampers with a copy of the committed evidence and asserts that the
specific check meant to catch that tampering reports FAIL. A harness that always
passes would prove nothing, so every check added in Stage A has a mutation here
that makes it fire.

These tests deliberately do not import ``adversarial_ai`` either --- the point of
the harness is that it shares no code with the pipeline it verifies, and
``test_harness_imports_no_repository_code`` asserts that property directly.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    # The repository has no packaging config, so tests reach the harness the same
    # way the CLI does: from the checkout root.
    sys.path.insert(0, str(REPO_ROOT))

from verification.stage_a_clean_recompute import (  # noqa: E402
    VerificationError,
    load_classes,
    load_declared_models,
    main,
    recompute_classification_report,
    recompute_confusion_matrix,
    run_stage_a,
)

MODEL = "cnn_baseline"
HARNESS_SOURCE = REPO_ROOT / "verification" / "stage_a_clean_recompute.py"


# --- Fixtures and helpers ---------------------------------------------------


@pytest.fixture
def evidence_root(tmp_path: Path) -> Path:
    """A disposable copy of the committed evidence Stage A reads."""
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "configs", root / "configs")
    shutil.copytree(REPO_ROOT / "results" / "clean", root / "results" / "clean")
    return root


def _clean_dir(root: Path) -> Path:
    return root / "results" / "clean"


def _eval_csv(root: Path) -> Path:
    return _clean_dir(root) / f"{MODEL}_eval.csv"


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        return list(reader), fieldnames


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _probability_columns(root: Path) -> list[str]:
    classes = load_classes(root / "configs" / "classes.json")
    return [f"prob_{index}_{label}" for index, label in enumerate(classes)]


def _set_probability_row(root: Path, row_index: int, values: list[float]) -> None:
    """Overwrite one row's probability vector, leaving every other column intact."""
    path = _eval_csv(root)
    rows, fieldnames = _read_csv(path)
    for column, value in zip(_probability_columns(root), values):
        rows[row_index][column] = repr(value)
    _write_csv(path, rows, fieldnames)


def _one_hot(root: Path, hot_index: int, value: float = 1.0) -> list[float]:
    count = len(_probability_columns(root))
    vector = [0.0] * count
    vector[hot_index] = value
    return vector


def _run(root: Path) -> dict[str, Any]:
    return run_stage_a(root)


def _check(report: dict[str, Any], name: str) -> dict[str, Any]:
    """Return the named check for MODEL, asserting it was actually run."""
    models = {model["model"]: model for model in report["models"]}
    assert MODEL in models, f"model {MODEL} missing from report"
    checks = {check["name"]: check for check in models[MODEL]["checks"]}
    assert name in checks, f"check {name} was not run; ran {sorted(checks)}"
    return checks[name]


def _assert_only_failure(report: dict[str, Any], name: str) -> None:
    """Assert the report failed, and that the named check is among the failures."""
    assert report["status"] == "FAIL"
    assert _check(report, name)["status"] == "FAIL"


# --- Positive control -------------------------------------------------------


def test_untampered_evidence_passes(evidence_root: Path) -> None:
    """Guards against a harness that fails on everything."""
    report = _run(evidence_root)
    assert report["status"] == "PASS", report
    for model in report["models"]:
        assert model["failed_checks"] == 0
        assert model["checks"], "a model with no checks must not count as a pass"


def test_committed_repository_evidence_passes() -> None:
    """Stage A reproduces the committed Clean results in this checkout."""
    report = _run(REPO_ROOT)
    assert report["status"] == "PASS", report


# --- Independence -----------------------------------------------------------


def test_harness_imports_no_repository_code() -> None:
    """The harness must not import the pipeline it verifies, nor heavy numerics."""
    source = HARNESS_SOURCE.read_text(encoding="utf-8")
    import_lines = [
        line.strip()
        for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    forbidden = ("adversarial_ai", "pandas", "numpy", "sklearn", "scikit", "tensorflow", "keras")
    offenders = [
        line for line in import_lines if any(token in line for token in forbidden)
    ]
    assert not offenders, f"harness must stay independent, found: {offenders}"


def test_harness_does_not_modify_committed_evidence(evidence_root: Path, tmp_path: Path) -> None:
    """Running Stage A leaves every input byte-identical."""

    def digest() -> dict[str, str]:
        return {
            str(path.relative_to(evidence_root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(evidence_root.rglob("*"))
            if path.is_file()
        }

    before = digest()
    exit_code = main(
        ["--repo-root", str(evidence_root), "--output", str(tmp_path / "report.json")]
    )
    assert exit_code == 0
    assert digest() == before


# --- Probability column mutations -------------------------------------------


def test_mutation_non_finite_probability(evidence_root: Path) -> None:
    _set_probability_row(evidence_root, 0, _one_hot(evidence_root, 0, float("nan")))
    _assert_only_failure(_run(evidence_root), "clean.probabilities.finite")


def test_mutation_probability_out_of_range(evidence_root: Path) -> None:
    rows, _ = _read_csv(_eval_csv(evidence_root))
    predicted = int(rows[0]["predicted_index"])
    vector = [0.0] * len(_probability_columns(evidence_root))
    vector[predicted] = 1.5
    vector[(predicted + 1) % len(vector)] = -0.5  # keeps the row sum at 1.0
    _set_probability_row(evidence_root, 0, vector)

    report = _run(evidence_root)
    _assert_only_failure(report, "clean.probabilities.range")
    assert _check(report, "clean.probabilities.row_sum")["status"] == "PASS"


def test_mutation_probability_row_does_not_sum_to_one(evidence_root: Path) -> None:
    rows, _ = _read_csv(_eval_csv(evidence_root))
    predicted = int(rows[0]["predicted_index"])
    # Argmax still lands on predicted_index, so only the row sum breaks.
    _set_probability_row(evidence_root, 0, _one_hot(evidence_root, predicted, 0.9))

    report = _run(evidence_root)
    _assert_only_failure(report, "clean.probabilities.row_sum")
    assert _check(report, "clean.probabilities.argmax_matches_predicted_index")["status"] == "PASS"
    assert _check(report, "clean.probabilities.finite")["status"] == "PASS"


def test_mutation_probability_argmax_tie(evidence_root: Path) -> None:
    rows, _ = _read_csv(_eval_csv(evidence_root))
    predicted = int(rows[0]["predicted_index"])
    vector = [0.0] * len(_probability_columns(evidence_root))
    vector[predicted] = 0.5
    vector[(predicted + 1) % len(vector)] = 0.5
    _set_probability_row(evidence_root, 0, vector)

    report = _run(evidence_root)
    _assert_only_failure(report, "clean.probabilities.argmax_unique")
    assert _check(report, "clean.probabilities.row_sum")["status"] == "PASS"


def test_mutation_probability_argmax_disagrees_with_predicted_index(evidence_root: Path) -> None:
    rows, _ = _read_csv(_eval_csv(evidence_root))
    predicted = int(rows[0]["predicted_index"])
    other = (predicted + 1) % len(_probability_columns(evidence_root))
    _set_probability_row(evidence_root, 0, _one_hot(evidence_root, other))

    report = _run(evidence_root)
    _assert_only_failure(report, "clean.probabilities.argmax_matches_predicted_index")
    evidence = _check(report, "clean.probabilities.argmax_matches_predicted_index")["evidence"]
    assert evidence["offending_count"] == 1
    assert evidence["sample"][0]["argmax_index"] == other
    assert evidence["sample"][0]["declared_predicted_index"] == predicted


def test_mutation_predicted_label_disagrees_with_class_map(evidence_root: Path) -> None:
    path = _eval_csv(evidence_root)
    rows, fieldnames = _read_csv(path)
    rows[0]["predicted_label"] = "Tug" if rows[0]["predicted_label"] != "Tug" else "Bulkers"
    _write_csv(path, rows, fieldnames)
    _assert_only_failure(_run(evidence_root), "clean.predicted_index_matches_predicted_label")


def test_mutation_true_label_disagrees_with_class_map(evidence_root: Path) -> None:
    path = _eval_csv(evidence_root)
    rows, fieldnames = _read_csv(path)
    rows[0]["true_label"] = "Tug" if rows[0]["true_label"] != "Tug" else "Bulkers"
    _write_csv(path, rows, fieldnames)
    _assert_only_failure(_run(evidence_root), "clean.true_index_matches_true_label")


# --- Confusion matrix mutations ---------------------------------------------


def test_mutation_confusion_matrix_cell(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_confusion_matrix.csv"
    matrix = [row.split(",") for row in path.read_text(encoding="utf-8").strip().splitlines()]
    matrix[0][0] = str(int(matrix[0][0]) + 1)
    path.write_text("\n".join(",".join(row) for row in matrix) + "\n", encoding="utf-8")

    report = _run(evidence_root)
    _assert_only_failure(report, "clean.confusion_matrix.cells")
    assert _check(report, "clean.confusion_matrix.cells")["evidence"]["offending_count"] == 1


def test_mutation_confusion_matrix_shape(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_confusion_matrix.csv"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    _assert_only_failure(_run(evidence_root), "clean.confusion_matrix.shape")


def test_mutation_confusion_matrix_non_integer(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_confusion_matrix.csv"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    lines[0] = "not-a-number" + lines[0][lines[0].index(",") :]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _assert_only_failure(_run(evidence_root), "clean.evidence.readable")


# --- Classification report mutations ----------------------------------------


def test_mutation_report_json_value(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_report.json"
    report_payload = _read_json(path)
    report_payload["macro avg"]["f1-score"] += 0.01
    _write_json(path, report_payload)
    _assert_only_failure(_run(evidence_root), "clean.report_json.values")


def test_mutation_report_json_accuracy_scalar(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_report.json"
    report_payload = _read_json(path)
    report_payload["accuracy"] = 0.99
    _write_json(path, report_payload)
    _assert_only_failure(_run(evidence_root), "clean.report_json.values")


def test_mutation_report_json_missing_section(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_report.json"
    report_payload = _read_json(path)
    report_payload.pop("weighted avg")
    _write_json(path, report_payload)
    _assert_only_failure(_run(evidence_root), "clean.report_json.keys")


def test_mutation_report_json_value_is_not_numeric(evidence_root: Path) -> None:
    """A non-numeric metric must fail, not slip past the comparison."""
    path = _clean_dir(evidence_root) / f"{MODEL}_report.json"
    report_payload = _read_json(path)
    report_payload["macro avg"]["f1-score"] = "0.661057169301309"
    _write_json(path, report_payload)
    _assert_only_failure(_run(evidence_root), "clean.report_json.values")


def test_mutation_report_csv_value(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_report.csv"
    rows, fieldnames = _read_csv(path)
    rows[0]["precision"] = str(float(rows[0]["precision"]) + 0.01)
    _write_csv(path, rows, fieldnames)
    _assert_only_failure(_run(evidence_root), "clean.report_csv.values")


def test_mutation_report_csv_missing_section(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_report.csv"
    rows, fieldnames = _read_csv(path)
    _write_csv(path, rows[:-1], fieldnames)
    _assert_only_failure(_run(evidence_root), "clean.report_csv.sections")


# --- Summary JSON mutations -------------------------------------------------


def test_mutation_summary_macro_f1(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_summary.json"
    summary = _read_json(path)
    summary["macro_f1"] += 1e-6
    _write_json(path, summary)
    _assert_only_failure(_run(evidence_root), "clean.summary_json.headline_metrics")


def test_mutation_summary_correct_predictions(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_summary.json"
    summary = _read_json(path)
    summary["correct_predictions"] = int(summary["correct_predictions"]) + 1
    _write_json(path, summary)
    _assert_only_failure(_run(evidence_root), "clean.summary_json.headline_metrics")


def test_mutation_summary_accuracy_beyond_float32_tolerance(evidence_root: Path) -> None:
    """The float32 allowance must not be wide enough to hide a real drift."""
    path = _clean_dir(evidence_root) / f"{MODEL}_summary.json"
    summary = _read_json(path)
    summary["test_accuracy"] = float(summary["test_accuracy"]) + 1e-4
    _write_json(path, summary)
    _assert_only_failure(_run(evidence_root), "clean.summary_json.headline_metrics")


def test_mutation_summary_missing_field(evidence_root: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_summary.json"
    summary = _read_json(path)
    summary.pop("macro_f1")
    _write_json(path, summary)
    _assert_only_failure(_run(evidence_root), "clean.summary_json.headline_metrics")


# --- Fail-closed behaviour --------------------------------------------------


def test_missing_eval_csv_fails_closed(evidence_root: Path) -> None:
    """Deleting evidence must fail the run, not shrink the verified set."""
    _eval_csv(evidence_root).unlink()
    report = _run(evidence_root)
    assert report["status"] == "FAIL"
    # The model is still declared in experiment.yaml, so it is still verified.
    assert MODEL in {model["model"] for model in report["models"]}
    assert _check(report, "clean.evidence.readable")["status"] == "FAIL"


def test_deleting_every_artefact_for_a_model_still_fails(evidence_root: Path) -> None:
    """A model cannot be hidden by removing all of its result files."""
    for path in _clean_dir(evidence_root).glob(f"{MODEL}_*"):
        path.unlink()
    report = _run(evidence_root)
    assert report["status"] == "FAIL"
    assert MODEL in {model["model"] for model in report["models"]}
    assert report["roster_mismatch"]["declared_but_missing"] == [MODEL]


def test_undeclared_model_artefacts_fail_closed(evidence_root: Path) -> None:
    """Results for a model the config never declares are a mismatch, not a pass."""
    shutil.copy2(
        _eval_csv(evidence_root), _clean_dir(evidence_root) / "ghost_model_eval.csv"
    )
    report = _run(evidence_root)
    assert report["status"] == "FAIL"
    assert report["roster_mismatch"]["present_but_undeclared"] == ["ghost_model"]


def test_missing_experiment_config_fails_closed(evidence_root: Path) -> None:
    (evidence_root / "configs" / "experiment.yaml").unlink()
    report = _run(evidence_root)
    assert report["status"] == "FAIL"
    assert "failure" in report
    assert report["models"] == []


def test_declared_models_match_the_committed_config() -> None:
    assert load_declared_models(REPO_ROOT / "configs" / "experiment.yaml") == [
        "cnn_baseline",
        "mobilenet",
    ]


def test_load_declared_models_rejects_an_empty_roster(tmp_path: Path) -> None:
    path = tmp_path / "experiment.yaml"
    path.write_text("models:\ndataset:\n  x: 1\n", encoding="utf-8")
    with pytest.raises(VerificationError):
        load_declared_models(path)


def test_load_declared_models_rejects_a_missing_block(tmp_path: Path) -> None:
    path = tmp_path / "experiment.yaml"
    path.write_text("dataset:\n  num_classes: 10\n", encoding="utf-8")
    with pytest.raises(VerificationError):
        load_declared_models(path)


def test_load_declared_models_ignores_comments_and_nested_keys(tmp_path: Path) -> None:
    path = tmp_path / "experiment.yaml"
    path.write_text(
        "dataset:\n"
        "  num_classes: 10\n"
        "\n"
        "models:  # roster\n"
        "  alpha:\n"
        "    file: models/alpha.h5\n"
        "  beta:\n"
        "    file: models/beta.h5\n"
        "\n"
        "attacks:\n"
        "  fgsm:\n"
        "    steps: 1\n",
        encoding="utf-8",
    )
    assert load_declared_models(path) == ["alpha", "beta"]


def test_missing_report_json_fails_closed(evidence_root: Path) -> None:
    (_clean_dir(evidence_root) / f"{MODEL}_report.json").unlink()
    _assert_only_failure(_run(evidence_root), "clean.evidence.readable")


def test_missing_confusion_matrix_fails_closed(evidence_root: Path) -> None:
    (_clean_dir(evidence_root) / f"{MODEL}_confusion_matrix.csv").unlink()
    _assert_only_failure(_run(evidence_root), "clean.evidence.readable")


def test_unparsable_probability_fails_closed(evidence_root: Path) -> None:
    path = _eval_csv(evidence_root)
    rows, fieldnames = _read_csv(path)
    rows[0][_probability_columns(evidence_root)[0]] = "n/a"
    _write_csv(path, rows, fieldnames)
    _assert_only_failure(_run(evidence_root), "clean.evidence.readable")


def test_predicted_index_outside_class_map_fails_closed(evidence_root: Path) -> None:
    path = _eval_csv(evidence_root)
    rows, fieldnames = _read_csv(path)
    rows[0]["predicted_index"] = "99"
    _write_csv(path, rows, fieldnames)
    _assert_only_failure(_run(evidence_root), "clean.evidence.readable")


def test_probability_column_label_mismatch_fails_closed(evidence_root: Path) -> None:
    """A probability column renamed away from the class map must not be ignored."""
    path = _eval_csv(evidence_root)
    rows, fieldnames = _read_csv(path)
    original = _probability_columns(evidence_root)[0]
    renamed = "prob_0_Wrong Label"
    fieldnames[fieldnames.index(original)] = renamed
    for row in rows:
        row[renamed] = row.pop(original)
    _write_csv(path, rows, fieldnames)
    _assert_only_failure(_run(evidence_root), "clean.evidence.readable")


def test_missing_classes_config_fails_closed(evidence_root: Path) -> None:
    (evidence_root / "configs" / "classes.json").unlink()
    report = _run(evidence_root)
    assert report["status"] == "FAIL"
    assert "failure" in report
    assert report["models"] == []


def test_no_clean_results_fails_closed(evidence_root: Path) -> None:
    """An emptied results directory must fail, not vacuously pass."""
    for path in _clean_dir(evidence_root).glob("*"):
        path.unlink()
    report = _run(evidence_root)
    assert report["status"] == "FAIL"
    assert sorted(report["roster_mismatch"]["declared_but_missing"]) == [
        "cnn_baseline",
        "mobilenet",
    ]


# --- CLI --------------------------------------------------------------------


def test_cli_exit_code_and_report_file(evidence_root: Path, tmp_path: Path) -> None:
    output = tmp_path / "nested" / "report.json"
    assert main(["--repo-root", str(evidence_root), "--output", str(output)]) == 0
    payload = _read_json(output)
    assert payload["status"] == "PASS"
    assert payload["imports_repository_code"] is False
    assert payload["third_party_dependencies"] == []
    # The artefact must stay machine-independent: relative paths, no checkout root.
    assert "repo_root" not in payload
    for model in payload["models"]:
        for recorded in model["inputs"].values():
            assert recorded.startswith("results/clean/"), recorded


def test_cli_exit_code_is_nonzero_on_mismatch(evidence_root: Path, tmp_path: Path) -> None:
    path = _clean_dir(evidence_root) / f"{MODEL}_summary.json"
    summary = _read_json(path)
    summary["macro_f1"] = 0.5
    _write_json(path, summary)

    output = tmp_path / "report.json"
    assert main(["--repo-root", str(evidence_root), "--output", str(output)]) == 1
    assert _read_json(output)["status"] == "FAIL"


# --- Metric definitions -----------------------------------------------------


def test_recompute_report_on_a_hand_checked_example() -> None:
    """Pin the metric definitions to values that can be verified by hand."""
    classes = ["a", "b"]
    true_labels = ["a", "a", "b", "b"]
    predicted_labels = ["a", "b", "b", "b"]

    report = recompute_classification_report(true_labels, predicted_labels, classes)

    # class a: tp=1, predicted=1 -> precision 1.0; support 2 -> recall 0.5
    assert report["a"]["precision"] == pytest.approx(1.0)
    assert report["a"]["recall"] == pytest.approx(0.5)
    assert report["a"]["f1-score"] == pytest.approx(2 / 3)
    # class b: tp=2, predicted=3 -> precision 2/3; support 2 -> recall 1.0
    assert report["b"]["precision"] == pytest.approx(2 / 3)
    assert report["b"]["recall"] == pytest.approx(1.0)
    assert report["b"]["f1-score"] == pytest.approx(0.8)

    assert report["accuracy"] == pytest.approx(0.75)
    assert report["macro avg"]["f1-score"] == pytest.approx((2 / 3 + 0.8) / 2)
    assert report["weighted avg"]["f1-score"] == pytest.approx((2 / 3 + 0.8) / 2)
    assert report["macro avg"]["support"] == 4.0


def test_recompute_report_handles_a_class_with_no_predictions() -> None:
    """Zero division resolves to 0.0, matching the committed reports' convention."""
    report = recompute_classification_report(["a", "b"], ["a", "a"], ["a", "b", "c"])
    assert report["b"]["precision"] == 0.0
    assert report["b"]["recall"] == 0.0
    assert report["b"]["f1-score"] == 0.0
    assert report["c"]["precision"] == 0.0
    assert report["c"]["support"] == 0.0


def test_recompute_confusion_matrix_orientation() -> None:
    """Rows are true classes and columns are predictions."""
    matrix = recompute_confusion_matrix(["a", "a", "b"], ["a", "b", "b"], ["a", "b"])
    assert matrix == [[1, 1], [0, 1]]


def test_recompute_rejects_unknown_label() -> None:
    with pytest.raises(VerificationError):
        recompute_confusion_matrix(["a"], ["z"], ["a", "b"])


def test_load_classes_rejects_non_contiguous_indices(tmp_path: Path) -> None:
    path = tmp_path / "classes.json"
    path.write_text(json.dumps({"0": "a", "2": "b"}), encoding="utf-8")
    with pytest.raises(VerificationError):
        load_classes(path)
