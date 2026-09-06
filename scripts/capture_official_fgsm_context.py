"""Capture immutable context before running the official FGSM candidate sweep."""

from __future__ import annotations

import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from adversarial_ai.evaluation.clean_baseline import package_version


OUTPUT = Path("results/attacks/official_candidate")
PROTECTED = [
    "models",
    "configs/test_manifest.json",
    "results/clean",
    "results/attacks/provisional",
    "src/adversarial_ai/attacks",
    "src/adversarial_ai/evaluation",
]


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()


def main() -> None:
    import tensorflow as tf

    dirty = _git("status", "--short", "--", *PROTECTED).splitlines()
    if dirty:
        raise SystemExit(f"Protected research inputs are dirty; stop before execution: {dirty}")
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        raise SystemExit(f"Candidate directory is not empty: {OUTPUT}")

    source_sha = _git("rev-parse", "HEAD")
    all_status = _git("status", "--short").splitlines()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    context = {
        "schema_version": 1,
        "source_commit_sha": source_sha,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_status_short": all_status,
        "python": platform.python_version(),
        "tensorflow": tf.__version__,
        "keras": package_version("keras"),
        "platform": platform.platform(),
        "output_dir": OUTPUT.as_posix(),
        "epsilons": [0.0, 0.01, 0.03, 0.05],
    }
    path = OUTPUT / "official_execution_context.json"
    path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    print(path)
    print(source_sha)


if __name__ == "__main__":
    main()
