"""CLI entry point for CNN FGSM evaluation."""

from adversarial_ai.evaluation.fgsm_evaluation import run_cli


if __name__ == "__main__":
    run_cli("cnn", "models/cnn_baseline.h5", 128)
