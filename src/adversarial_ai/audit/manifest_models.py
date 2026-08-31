"""Audit manifest and model files integrity against canonical specifications."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from adversarial_ai.audit.exceptions import AuditError

EXPECTED_TEST_SAMPLES = 781
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 hash of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_manifest(manifest_path: Path, data_dir: Path | None = None) -> dict[str, Any]:
    """Audit test_manifest.json structure, records, SHA-256 formats, and image contents if present.

    Returns summary details of audited manifest items.
    """
    if not manifest_path.is_file():
        raise AuditError(f"Manifest file missing: {manifest_path}")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AuditError(f"Failed to parse manifest JSON: {manifest_path}", {"error": str(exc)}) from exc

    if not isinstance(manifest, dict):
        raise AuditError("Manifest root must be an object")

    test_samples = manifest.get("test_samples")
    if test_samples != EXPECTED_TEST_SAMPLES:
        raise AuditError(
            f"Manifest test_samples must be {EXPECTED_TEST_SAMPLES}, got {test_samples}",
            {"expected": EXPECTED_TEST_SAMPLES, "actual": test_samples},
        )

    test_files = manifest.get("test_files")
    if not isinstance(test_files, list):
        raise AuditError("Manifest test_files must be a list")

    if len(test_files) != EXPECTED_TEST_SAMPLES:
        raise AuditError(
            f"Manifest test_files length must be {EXPECTED_TEST_SAMPLES}, got {len(test_files)}",
            {"expected": EXPECTED_TEST_SAMPLES, "actual": len(test_files)},
        )

    seen_paths: set[str] = set()
    verified_images = 0

    for idx, record in enumerate(test_files):
        if not isinstance(record, dict):
            raise AuditError(f"test_files[{idx}] must be a dict")

        missing = {"relative_path", "label", "sha256"} - record.keys()
        if missing:
            raise AuditError(f"test_files[{idx}] missing required fields: {sorted(missing)}")

        rel_path = record["relative_path"]
        label = record["label"]
        sha256_val = record["sha256"]

        if not isinstance(rel_path, str) or not rel_path.strip():
            raise AuditError(f"test_files[{idx}].relative_path must be a non-empty string")
        if not isinstance(label, str) or not label.strip():
            raise AuditError(f"test_files[{idx}].label must be a non-empty string")
        if not isinstance(sha256_val, str) or not _SHA256_RE.fullmatch(sha256_val):
            raise AuditError(f"test_files[{idx}].sha256 must be a lowercase 64-char hex SHA-256 digest")

        normalized_path = PurePosixPath(rel_path.replace("\\", "/")).as_posix()
        if normalized_path in seen_paths:
            raise AuditError(f"Duplicate relative_path in manifest: {normalized_path!r}")
        seen_paths.add(normalized_path)

        # Label consistency check
        first_part = PurePosixPath(normalized_path).parts[0]
        if first_part != label:
            raise AuditError(
                f"test_files[{idx}] label {label!r} differs from path class {first_part!r}",
                {"path": normalized_path, "label": label, "path_class": first_part},
            )

        # Content verification if data_dir provided and image file exists
        if data_dir is not None:
            image_file = data_dir / normalized_path
            if image_file.is_file():
                actual_sha = sha256_file(image_file)
                if actual_sha != sha256_val:
                    raise AuditError(
                        f"Image content SHA-256 mismatch for {normalized_path!r}",
                        {"expected": sha256_val, "actual": actual_sha},
                    )
                verified_images += 1

    models = manifest.get("models")
    if not isinstance(models, list) or not models:
        raise AuditError("Manifest models must be a non-empty list")

    manifest_models: dict[str, str] = {}
    for idx, model_rec in enumerate(models):
        if not isinstance(model_rec, dict):
            raise AuditError(f"models[{idx}] must be a dict")
        missing = {"path", "sha256"} - model_rec.keys()
        if missing:
            raise AuditError(f"models[{idx}] missing fields: {sorted(missing)}")
        m_path = PurePosixPath(model_rec["path"].replace("\\", "/")).as_posix()
        m_sha = model_rec["sha256"]
        if not isinstance(m_sha, str) or not _SHA256_RE.fullmatch(m_sha):
            raise AuditError(f"models[{idx}].sha256 must be a lowercase 64-char hex SHA-256 digest")
        manifest_models[m_path] = m_sha

    return {
        "manifest_path": str(manifest_path),
        "test_samples": test_samples,
        "verified_image_files": verified_images,
        "images_present": verified_images > 0,
        "manifest_models": manifest_models,
    }


def audit_models(
    manifest_models: dict[str, str],
    metadata_files: list[Path],
    repo_root: Path = Path("."),
) -> dict[str, Any]:
    """Audit model SHA-256 consistency across manifest, metadata JSON files, and disk files (if present)."""
    audited_models: dict[str, dict[str, Any]] = {}

    for metadata_file in metadata_files:
        if not metadata_file.is_file():
            continue
        try:
            meta = json.loads(metadata_file.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AuditError(f"Failed to read metadata JSON: {metadata_file}", {"error": str(exc)}) from exc

        model_path = meta.get("model_path")
        model_sha = meta.get("model_sha256")

        if not model_path or not model_sha:
            continue

        normalized_path = PurePosixPath(model_path.replace("\\", "/")).as_posix()

        if normalized_path not in manifest_models:
            raise AuditError(
                f"Model path {normalized_path!r} referenced in {metadata_file} is absent from manifest models",
                {"metadata_file": str(metadata_file), "model_path": normalized_path},
            )

        expected_sha = manifest_models[normalized_path]
        if model_sha != expected_sha:
            raise AuditError(
                f"Model SHA-256 mismatch between {metadata_file} ({model_sha}) and manifest ({expected_sha})",
                {"metadata_file": str(metadata_file), "metadata_sha": model_sha, "manifest_sha": expected_sha},
            )

        disk_file = repo_root / normalized_path
        disk_present = disk_file.is_file()
        if disk_present:
            actual_sha = sha256_file(disk_file)
            if actual_sha != expected_sha:
                raise AuditError(
                    f"Model file on disk SHA-256 mismatch for {normalized_path!r}",
                    {"expected": expected_sha, "actual": actual_sha},
                )

        audited_models[normalized_path] = {
            "expected_sha256": expected_sha,
            "metadata_verified": True,
            "disk_file_present": disk_present,
            "disk_sha256_verified": disk_present,
        }

    return audited_models
