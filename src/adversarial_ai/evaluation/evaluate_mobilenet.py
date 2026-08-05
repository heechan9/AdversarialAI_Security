"""CLI entry point for the finetuned MobileNetV2 clean baseline."""

from adversarial_ai.evaluation.clean_baseline import run_cli


if __name__ == "__main__":
    run_cli("mobilenet", "models/mobilenet_finetuned.h5", 224)
