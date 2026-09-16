"""CLI entry point for MobileNetV2 FGSM evaluation."""

from adversarial_ai.evaluation.fgsm_evaluation import run_cli


if __name__ == "__main__":
    run_cli("mobilenet", "models/mobilenet_finetuned.h5", 224)
