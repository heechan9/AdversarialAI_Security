"""Reproducible clean-baseline evaluation for directory-based ship data."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix


@dataclass(frozen=True)
class EvaluationSpec:
    name: str
    model_path: Path
    image_size: tuple[int, int]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_expected_classes(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    indexed = sorted(((int(index), name) for index, name in payload.items()))
    return [name for _, name in indexed]


def validate_class_mapping(actual: dict[str, int], expected: Sequence[str]) -> None:
    expected_mapping = {name: index for index, name in enumerate(expected)}
    if actual != expected_mapping:
        raise ValueError(
            "Dataset class mapping differs from configs/classes.json: "
            f"actual={actual!r}, expected={expected_mapping!r}"
        )


def build_prediction_frame(
    filepaths: Sequence[str],
    y_true: np.ndarray,
    probabilities: np.ndarray,
    class_names: Sequence[str],
    data_root: Path,
) -> pd.DataFrame:
    if len(filepaths) != len(y_true) or len(y_true) != len(probabilities):
        raise ValueError("File, label, and prediction counts must match")
    y_pred = np.argmax(probabilities, axis=1)
    rows: dict[str, Any] = {
        "relative_path": [
            Path(path).resolve().relative_to(data_root.resolve()).as_posix()
            for path in filepaths
        ],
        "true_index": y_true.astype(int),
        "true_label": [class_names[index] for index in y_true],
        "predicted_index": y_pred.astype(int),
        "predicted_label": [class_names[index] for index in y_pred],
        "correct": y_true == y_pred,
    }
    for index, class_name in enumerate(class_names):
        rows[f"prob_{index}_{class_name}"] = probabilities[:, index]
    return pd.DataFrame(rows)


def save_confusion_matrix(
    matrix: np.ndarray, class_names: Sequence[str], output_path: Path
) -> None:
    figure, axis = plt.subplots(figsize=(11, 9))
    image = axis.imshow(matrix, interpolation="nearest", cmap="Blues")
    figure.colorbar(image, ax=axis)
    axis.set(
        xticks=np.arange(len(class_names)),
        yticks=np.arange(len(class_names)),
        xticklabels=class_names,
        yticklabels=class_names,
        xlabel="Predicted label",
        ylabel="True label",
        title="Clean baseline confusion matrix",
    )
    plt.setp(axis.get_xticklabels(), rotation=45, ha="right")
    threshold = matrix.max() / 2 if matrix.size else 0
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            axis.text(
                column,
                row,
                str(matrix[row, column]),
                ha="center",
                va="center",
                color="white" if matrix[row, column] > threshold else "black",
            )
    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def evaluate(spec: EvaluationSpec, data_dir: Path, classes_path: Path, output_dir: Path) -> None:
    # TensorFlow is intentionally imported lazily so pure utility tests do not
    # require the heavy runtime.
    import tensorflow as tf

    class_names = load_expected_classes(classes_path)
    generator = tf.keras.preprocessing.image.ImageDataGenerator(rescale=1.0 / 255.0)
    test_generator = generator.flow_from_directory(
        str(data_dir),
        target_size=spec.image_size,
        batch_size=32,
        class_mode="categorical",
        shuffle=False,
    )
    validate_class_mapping(test_generator.class_indices, class_names)
    if test_generator.samples != 781:
        raise ValueError(f"Expected 781 test images, found {test_generator.samples}")

    model = tf.keras.models.load_model(spec.model_path)
    weights_before = [weight.numpy().copy() for weight in model.weights]
    evaluation = model.evaluate(test_generator, verbose=1, return_dict=True)
    if "loss" not in evaluation or "accuracy" not in evaluation:
        raise ValueError(f"Model evaluation must expose loss and accuracy, got {evaluation.keys()}")
    loss = float(evaluation["loss"])
    accuracy = float(evaluation["accuracy"])
    probabilities = model.predict(test_generator, verbose=1)
    if not np.isfinite(probabilities).all():
        raise ValueError("Predictions contain NaN or Inf")
    if any(not np.array_equal(before, after.numpy()) for before, after in zip(weights_before, model.weights)):
        raise RuntimeError("Evaluation unexpectedly changed model weights")

    y_true = test_generator.classes.astype(int)
    y_pred = np.argmax(probabilities, axis=1)
    report = classification_report(
        y_true,
        y_pred,
        labels=np.arange(len(class_names)),
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(y_true, y_pred, labels=np.arange(len(class_names)))

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = spec.name
    predictions = build_prediction_frame(
        test_generator.filepaths, y_true, probabilities, class_names, data_dir
    )
    predictions.to_csv(output_dir / f"{prefix}_eval.csv", index=False)
    pd.DataFrame(report).transpose().to_csv(output_dir / f"{prefix}_report.csv")
    (output_dir / f"{prefix}_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    np.savetxt(output_dir / f"{prefix}_confusion_matrix.csv", matrix, fmt="%d", delimiter=",")
    save_confusion_matrix(matrix, class_names, output_dir / f"{prefix}_confusion_matrix.png")

    summary = {
        "model": prefix,
        "test_samples": int(len(y_true)),
        "test_loss": loss,
        "test_accuracy": accuracy,
        "correct_predictions": int((y_true == y_pred).sum()),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "weighted_f1": float(report["weighted avg"]["f1-score"]),
    }
    (output_dir / f"{prefix}_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    metadata = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "tensorflow": tf.__version__,
        "keras": package_version("keras"),
        "model_path": spec.model_path.as_posix(),
        "model_sha256": sha256_file(spec.model_path),
        "data_path": data_dir.as_posix(),
        "input_size": [*spec.image_size, 3],
        "normalization": "rescale=1./255",
        "class_mapping": test_generator.class_indices,
    }
    (output_dir / f"{prefix}_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def parse_args(default_name: str, default_model: str, default_size: int) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=Path(default_model))
    parser.add_argument("--data", type=Path, default=Path("data/test"))
    parser.add_argument("--classes", type=Path, default=Path("configs/classes.json"))
    parser.add_argument("--output", type=Path, default=Path("results/clean"))
    parser.add_argument("--name", default=default_name)
    parser.add_argument("--image-size", type=int, default=default_size)
    return parser.parse_args()


def run_cli(default_name: str, default_model: str, default_size: int) -> None:
    args = parse_args(default_name, default_model, default_size)
    evaluate(
        EvaluationSpec(args.name, args.model, (args.image_size, args.image_size)),
        args.data,
        args.classes,
        args.output,
    )
