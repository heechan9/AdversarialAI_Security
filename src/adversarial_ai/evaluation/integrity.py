"""Strict integrity validation for reproducible evaluation inputs."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


EXPECTED_TEST_SAMPLES = 781
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Return the SHA-256 digest of *path* without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    return value


def _require_sha256(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValueError(f"{context} must be a lowercase 64-character SHA-256")
    return value


def _normalize_relative_path(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} must be a non-empty relative path")
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        "\x00" in normalized
        or re.match(r"^[A-Za-z]:", normalized)
        or path.is_absolute()
        or path.drive
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError(f"{context} must not be absolute or escape the dataset root")
    return path.as_posix()


def _resolve_dataset_file(data_dir: Path, relative_path: str) -> Path:
    root = data_dir.absolute()
    if root.is_symlink():
        raise ValueError(f"Dataset path must not contain symlinks: {relative_path!r}")

    candidate = root
    for part in PurePosixPath(relative_path).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError(f"Dataset path must not contain symlinks: {relative_path!r}")

    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Dataset path escapes the dataset root: {relative_path!r}") from exc
    if not resolved_candidate.is_file():
        raise ValueError(f"Dataset path is not a regular file: {relative_path!r}")
    return resolved_candidate


def validate_reproducibility_manifest(
    *,
    manifest_path: Path,
    model_path: Path,
    dataset_filenames: Sequence[str],
    data_dir: Path,
    expected_samples: int = EXPECTED_TEST_SAMPLES,
) -> str:
    """Validate manifest structure, dataset content hashes, and model hash.

    Returns the verified model SHA-256. All paths in ``dataset_filenames`` are
    interpreted relative to ``data_dir`` and must appear in manifest order.
    """
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to read a valid manifest: {manifest_path}") from exc
    manifest = _require_mapping(manifest, "Manifest")

    if manifest.get("test_samples") != expected_samples:
        raise ValueError(f"Manifest must declare exactly {expected_samples} test samples")
    test_files = manifest.get("test_files")
    if not isinstance(test_files, list):
        raise ValueError("Manifest test_files must be an array")
    if len(test_files) != expected_samples:
        raise ValueError(f"Manifest test_files must contain exactly {expected_samples} entries")
    if len(dataset_filenames) != expected_samples:
        raise ValueError(f"Dataset must contain exactly {expected_samples} filenames")

    actual_paths = [
        _normalize_relative_path(value, f"dataset_filenames[{index}]")
        for index, value in enumerate(dataset_filenames)
    ]
    if len(set(actual_paths)) != len(actual_paths):
        raise ValueError("Dataset filenames contain duplicate relative paths")

    expected_paths: list[str] = []
    expected_hashes: list[str] = []
    for index, raw_record in enumerate(test_files):
        record = _require_mapping(raw_record, f"test_files[{index}]")
        missing = {"relative_path", "label", "sha256"} - record.keys()
        if missing:
            raise ValueError(f"test_files[{index}] is missing fields: {sorted(missing)}")
        relative_path = _normalize_relative_path(
            record["relative_path"], f"test_files[{index}].relative_path"
        )
        label = record["label"]
        if not isinstance(label, str) or not label:
            raise ValueError(f"test_files[{index}].label must be a non-empty string")
        if PurePosixPath(relative_path).parts[0] != label:
            raise ValueError(f"Label differs from the path class for {relative_path!r}")
        expected_paths.append(relative_path)
        expected_hashes.append(_require_sha256(record["sha256"], f"test_files[{index}].sha256"))

    if len(set(expected_paths)) != len(expected_paths):
        raise ValueError("Manifest contains duplicate relative paths")
    if expected_paths != actual_paths:
        raise ValueError("Dataset file order differs from the reproducibility manifest")

    for relative_path, expected_hash in zip(expected_paths, expected_hashes):
        actual_hash = sha256_file(_resolve_dataset_file(data_dir, relative_path))
        if actual_hash != expected_hash:
            raise ValueError(f"Dataset SHA-256 mismatch: {relative_path!r}")

    models = manifest.get("models")
    if not isinstance(models, list) or not models:
        raise ValueError("Manifest models must be a non-empty array")
    model_records: dict[str, str] = {}
    for index, raw_record in enumerate(models):
        record = _require_mapping(raw_record, f"models[{index}]")
        missing = {"path", "sha256"} - record.keys()
        if missing:
            raise ValueError(f"models[{index}] is missing fields: {sorted(missing)}")
        if not isinstance(record["path"], str) or not record["path"]:
            raise ValueError(f"models[{index}].path must be a non-empty string")
        key = Path(record["path"]).as_posix()
        if key in model_records:
            raise ValueError(f"Manifest contains duplicate model path: {key!r}")
        model_records[key] = _require_sha256(record["sha256"], f"models[{index}].sha256")

    model_key = model_path.as_posix()
    if model_key not in model_records:
        raise ValueError(f"Model {model_key!r} is absent from the manifest")
    if not model_path.is_file():
        raise ValueError(f"Model file is missing: {model_key!r}")
    actual_model_hash = sha256_file(model_path)
    if model_records[model_key] != actual_model_hash:
        raise ValueError("Model SHA-256 differs from the reproducibility manifest")
    return actual_model_hash
