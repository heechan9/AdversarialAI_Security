"""Generate reproducibility checksums without committing models or images."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from adversarial_ai.evaluation.clean_baseline import sha256_file


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def build_manifest(data_dir: Path, model_paths: list[Path]) -> dict:
    files = sorted(
        path for path in data_dir.rglob("*") if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if len(files) != 781:
        raise ValueError(f"Expected 781 test images, found {len(files)}")
    return {
        "data_root": data_dir.as_posix(),
        "test_samples": len(files),
        "test_files": [
            {
                "relative_path": path.relative_to(data_dir).as_posix(),
                "label": path.relative_to(data_dir).parts[0],
                "sha256": sha256_file(path),
            }
            for path in files
        ],
        "models": [
            {"path": path.as_posix(), "sha256": sha256_file(path)} for path in model_paths
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data/test"))
    parser.add_argument(
        "--models",
        type=Path,
        nargs="+",
        default=[Path("models/cnn_baseline.h5"), Path("models/mobilenet_finetuned.h5")],
    )
    parser.add_argument("--output", type=Path, default=Path("configs/test_manifest.json"))
    args = parser.parse_args()
    manifest = build_manifest(args.data, args.models)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
