"""Full-test-set FGSM evaluation with versioned metrics and artifacts."""

from __future__ import annotations

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from adversarial_ai.attacks.fgsm import generate_fgsm, infer_from_logits
from adversarial_ai.evaluation.clean_baseline import (
    EvaluationSpec,
    load_expected_classes,
    package_version,
    save_confusion_matrix,
    validate_class_mapping,
)
from adversarial_ai.evaluation.integrity import validate_reproducibility_manifest


def compute_untargeted_asr(
    y_true: np.ndarray, clean_pred: np.ndarray, adversarial_pred: np.ndarray
) -> tuple[float, int, int]:
    """Return ASR, successes, denominator using clean-correct samples only."""
    clean_correct = clean_pred == y_true
    denominator = int(clean_correct.sum())
    successes = int((clean_correct & (adversarial_pred != y_true)).sum())
    return (successes / denominator if denominator else 0.0, successes, denominator)



def _probabilities(outputs: Any, from_logits: bool) -> np.ndarray:
    import tensorflow as tf

    tensor = tf.nn.softmax(outputs, axis=1) if from_logits else outputs
    values = np.asarray(tensor)
    if not np.isfinite(values).all():
        raise ValueError("Model outputs contain NaN or Inf")
    return values


def _save_attack_sample(
    clean: np.ndarray,
    adversarial: np.ndarray,
    title: str,
    output_path: Path,
) -> None:
    delta = np.abs(adversarial - clean)
    scale = float(delta.max())
    visual_delta = delta / scale if scale > 0 else delta
    figure, axes = plt.subplots(1, 3, figsize=(10, 3.5))
    for axis, image, label in zip(
        axes, [clean, adversarial, visual_delta], ["Clean", "Adversarial", "|delta| normalized"]
    ):
        axis.imshow(np.clip(image, 0, 1))
        axis.set_title(label)
        axis.axis("off")
    figure.suptitle(title)
    figure.tight_layout()
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)


def _run_epsilon(
    model: Any,
    generator: Any,
    epsilon: float,
    from_logits: bool,
    class_names: Sequence[str],
    sample_dir: Path,
    sample_limit: int,
    model_name: str,
) -> dict[str, Any]:
    y_true_parts: list[np.ndarray] = []
    clean_probability_parts: list[np.ndarray] = []
    adversarial_probability_parts: list[np.ndarray] = []
    linf_parts: list[np.ndarray] = []
    samples_saved = {"success": 0, "failure": 0}

    for batch_index in range(len(generator)):
        images, labels = generator[batch_index]
        clean_outputs = model(images, training=False)
        adversarial_images = generate_fgsm(
            model, images, labels, epsilon, from_logits=from_logits
        )
        adversarial_outputs = model(adversarial_images, training=False)
        clean_probabilities = _probabilities(clean_outputs, from_logits)
        adversarial_probabilities = _probabilities(adversarial_outputs, from_logits)
        adversarial_array = np.asarray(adversarial_images)
        linf = np.max(np.abs(adversarial_array - images), axis=(1, 2, 3))
        if np.any(linf > epsilon + 1e-6):
            raise RuntimeError("Observed perturbation exceeds the requested epsilon")

        y_true = np.argmax(labels, axis=1)
        clean_pred = np.argmax(clean_probabilities, axis=1)
        adversarial_pred = np.argmax(adversarial_probabilities, axis=1)
        if epsilon > 0:
            for local_index in range(len(images)):
                if clean_pred[local_index] != y_true[local_index]:
                    continue
                category = "success" if adversarial_pred[local_index] != y_true[local_index] else "failure"
                if samples_saved[category] >= sample_limit:
                    continue
                global_index = batch_index * generator.batch_size + local_index
                title = (
                    f"{model_name} eps={epsilon:g} {category}: "
                    f"{class_names[y_true[local_index]]} -> {class_names[adversarial_pred[local_index]]}"
                )
                path = sample_dir / f"{model_name}_eps_{epsilon:g}_{category}_{global_index:04d}.png"
                _save_attack_sample(images[local_index], adversarial_array[local_index], title, path)
                samples_saved[category] += 1

        y_true_parts.append(y_true)
        clean_probability_parts.append(clean_probabilities)
        adversarial_probability_parts.append(adversarial_probabilities)
        linf_parts.append(linf)

    return {
        "y_true": np.concatenate(y_true_parts),
        "clean_probabilities": np.concatenate(clean_probability_parts),
        "adversarial_probabilities": np.concatenate(adversarial_probability_parts),
        "linf": np.concatenate(linf_parts),
    }


def evaluate_fgsm(
    spec: EvaluationSpec,
    data_dir: Path,
    classes_path: Path,
    output_dir: Path,
    epsilons: Sequence[float],
    sample_limit: int = 2,
    manifest_path: Path = Path("configs/test_manifest.json"),
) -> None:
    import tensorflow as tf

    if not epsilons or any(epsilon < 0 for epsilon in epsilons):
        raise ValueError("epsilons must be a non-empty sequence of non-negative values")
    if len(set(epsilons)) != len(epsilons):
        raise ValueError("epsilons must not contain duplicates")
    class_names = load_expected_classes(classes_path)
    data_generator = tf.keras.preprocessing.image.ImageDataGenerator(rescale=1.0 / 255.0)
    test_generator = data_generator.flow_from_directory(
        str(data_dir),
        target_size=spec.image_size,
        batch_size=32,
        class_mode="categorical",
        shuffle=False,
    )
    validate_class_mapping(test_generator.class_indices, class_names)
    if test_generator.samples != 781:
        raise ValueError(f"Expected 781 test images, found {test_generator.samples}")
    model_sha256 = validate_reproducibility_manifest(
        manifest_path=manifest_path,
        model_path=spec.model_path,
        dataset_filenames=test_generator.filenames,
        data_dir=data_dir,
    )

    model = tf.keras.models.load_model(spec.model_path)
    from_logits = infer_from_logits(model)
    weights_before = [weight.numpy().copy() for weight in model.weights]
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_dir = output_dir / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    reference_clean_pred: np.ndarray | None = None
    reference_y_true: np.ndarray | None = None

    for epsilon in epsilons:
        result = _run_epsilon(
            model,
            test_generator,
            float(epsilon),
            from_logits,
            class_names,
            sample_dir,
            sample_limit,
            spec.name,
        )
        y_true = result["y_true"]
        clean_probabilities = result["clean_probabilities"]
        adversarial_probabilities = result["adversarial_probabilities"]
        clean_pred = np.argmax(clean_probabilities, axis=1)
        adversarial_pred = np.argmax(adversarial_probabilities, axis=1)
        if reference_y_true is None:
            reference_y_true, reference_clean_pred = y_true, clean_pred
        elif not np.array_equal(reference_y_true, y_true) or not np.array_equal(
            reference_clean_pred, clean_pred
        ):
            raise RuntimeError("Clean sample order or predictions changed between epsilon runs")

        asr, successes, denominator = compute_untargeted_asr(y_true, clean_pred, adversarial_pred)
        robust_accuracy = accuracy_score(y_true, adversarial_pred)
        summary = {
            "epsilon": float(epsilon),
            "test_samples": int(len(y_true)),
            "clean_accuracy": float(accuracy_score(y_true, clean_pred)),
            "robust_accuracy": float(robust_accuracy),
            "accuracy_drop": float(accuracy_score(y_true, clean_pred) - robust_accuracy),
            "macro_f1": float(f1_score(y_true, adversarial_pred, average="macro", zero_division=0)),
            "untargeted_asr": float(asr),
            "attack_successes": successes,
            "asr_denominator_clean_correct": denominator,
            "linf_max": float(result["linf"].max()),
            "linf_mean": float(result["linf"].mean()),
        }
        summaries.append(summary)

        report = classification_report(
            y_true,
            adversarial_pred,
            labels=np.arange(len(class_names)),
            target_names=class_names,
            output_dict=True,
            zero_division=0,
        )
        token = f"eps_{epsilon:g}"
        (output_dir / f"fgsm_{spec.name}_{token}_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        matrix = confusion_matrix(y_true, adversarial_pred, labels=np.arange(len(class_names)))
        np.savetxt(
            output_dir / f"fgsm_{spec.name}_{token}_confusion_matrix.csv",
            matrix,
            fmt="%d",
            delimiter=",",
        )
        save_confusion_matrix(
            matrix,
            class_names,
            output_dir / f"fgsm_{spec.name}_{token}_confusion_matrix.png",
            title=f"FGSM {spec.name} confusion matrix (epsilon={epsilon:g})",
        )
        per_sample = pd.DataFrame(
            {
                "relative_path": test_generator.filenames,
                "epsilon": float(epsilon),
                "true_index": y_true,
                "true_label": [class_names[index] for index in y_true],
                "clean_predicted_index": clean_pred,
                "clean_predicted_label": [class_names[index] for index in clean_pred],
                "adversarial_predicted_index": adversarial_pred,
                "adversarial_predicted_label": [class_names[index] for index in adversarial_pred],
                "clean_correct": clean_pred == y_true,
                "attack_success": (clean_pred == y_true) & (adversarial_pred != y_true),
                "linf": result["linf"],
            }
        )
        per_sample.to_csv(output_dir / f"fgsm_{spec.name}_{token}_samples.csv", index=False)

    if 0.0 in epsilons:
        zero = next(item for item in summaries if item["epsilon"] == 0.0)
        if (
            zero["accuracy_drop"] != 0.0
            or zero["untargeted_asr"] != 0.0
            or zero["linf_max"] != 0.0
        ):
            raise RuntimeError("epsilon=0 did not reproduce the clean predictions and input")
    if any(not np.array_equal(before, after.numpy()) for before, after in zip(weights_before, model.weights)):
        raise RuntimeError("FGSM evaluation unexpectedly changed model weights")
    pd.DataFrame(summaries).to_csv(output_dir / f"fgsm_{spec.name}.csv", index=False)
    metadata = {
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "tensorflow": tf.__version__,
        "keras": package_version("keras"),
        "model": spec.name,
        "model_path": spec.model_path.as_posix(),
        "model_sha256": model_sha256,
        "manifest_path": manifest_path.as_posix(),
        "input_size": [*spec.image_size, 3],
        "input_range": [0, 1],
        "norm": "L-infinity",
        "attack": "untargeted FGSM, exactly one step",
        "loss": "categorical_crossentropy",
        "from_logits": from_logits,
        "epsilons": [float(value) for value in epsilons],
        "asr_denominator": "clean-correct samples only",
    }
    (output_dir / f"fgsm_{spec.name}_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run_cli(default_name: str, default_model: str, default_size: int) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=Path(default_model))
    parser.add_argument("--data", type=Path, default=Path("data/test"))
    parser.add_argument("--classes", type=Path, default=Path("configs/classes.json"))
    parser.add_argument("--output", type=Path, default=Path("results/attacks"))
    parser.add_argument("--manifest", type=Path, default=Path("configs/test_manifest.json"))
    parser.add_argument("--epsilons", type=float, nargs="+", default=[0.0, 0.01, 0.03, 0.05])
    parser.add_argument("--sample-limit", type=int, default=2)
    args = parser.parse_args()
    evaluate_fgsm(
        EvaluationSpec(default_name, args.model, (default_size, default_size)),
        args.data,
        args.classes,
        args.output,
        args.epsilons,
        args.sample_limit,
        args.manifest,
    )
