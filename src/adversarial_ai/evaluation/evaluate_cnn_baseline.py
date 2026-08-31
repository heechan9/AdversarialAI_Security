"""CLI entry point for the CNN clean baseline."""

from adversarial_ai.evaluation.clean_baseline import run_cli


if __name__ == "__main__":
    run_cli("cnn_baseline", "models/cnn_baseline.h5", 128)
