import hashlib
import json
from pathlib import Path

import pytest

from adversarial_ai.evaluation.integrity import validate_reproducibility_manifest


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@pytest.fixture()
def manifest_case(tmp_path: Path):
    data_dir = tmp_path / "test"
    filenames = []
    records = []
    for index in range(781):
        relative = f"Class{index % 10}/image_{index:04d}.jpg"
        content = f"image-{index}".encode()
        path = data_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        filenames.append(relative)
        records.append(
            {"relative_path": relative, "label": f"Class{index % 10}", "sha256": _sha(content)}
        )
    model = tmp_path / "model.h5"
    model.write_bytes(b"model")
    manifest = {
        "test_samples": 781,
        "test_files": records,
        "models": [{"path": model.as_posix(), "sha256": _sha(b"model")}],
    }
    manifest_path = tmp_path / "manifest.json"

    def write(payload=None):
        manifest_path.write_text(json.dumps(manifest if payload is None else payload), encoding="utf-8")
        return manifest_path

    return data_dir, filenames, model, manifest, write


def test_valid_manifest_verifies_all_781_images(manifest_case):
    data_dir, filenames, model, _, write = manifest_case
    assert validate_reproducibility_manifest(
        manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
    ) == _sha(b"model")


def test_rejects_manifest_header_list_count_mismatch(manifest_case):
    data_dir, filenames, model, manifest, write = manifest_case
    manifest["test_files"] = manifest["test_files"][:1]
    with pytest.raises(ValueError, match="test_files must contain exactly 781"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


def test_rejects_dataset_content_tampering(manifest_case):
    data_dir, filenames, model, _, write = manifest_case
    (data_dir / filenames[123]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="Dataset SHA-256 mismatch"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


def test_rejects_missing_dataset_file(manifest_case):
    data_dir, filenames, model, _, write = manifest_case
    (data_dir / filenames[10]).unlink()
    with pytest.raises(ValueError, match="not a regular file"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


def test_rejects_dataset_directory_instead_of_regular_file(manifest_case):
    data_dir, filenames, model, _, write = manifest_case
    path = data_dir / filenames[10]
    path.unlink()
    path.mkdir()
    with pytest.raises(ValueError, match="not a regular file"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


def test_rejects_order_change(manifest_case):
    data_dir, filenames, model, _, write = manifest_case
    filenames[0], filenames[1] = filenames[1], filenames[0]
    with pytest.raises(ValueError, match="file order differs"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


def test_rejects_duplicate_manifest_path(manifest_case):
    data_dir, filenames, model, manifest, write = manifest_case
    manifest["test_files"][1] = dict(manifest["test_files"][0])
    filenames[1] = filenames[0]
    with pytest.raises(ValueError, match="duplicate relative paths"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


@pytest.mark.parametrize("field", ["relative_path", "label", "sha256"])
def test_rejects_missing_required_image_field(manifest_case, field):
    data_dir, filenames, model, manifest, write = manifest_case
    del manifest["test_files"][0][field]
    with pytest.raises(ValueError, match="missing fields"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


def test_rejects_invalid_image_sha_format(manifest_case):
    data_dir, filenames, model, manifest, write = manifest_case
    manifest["test_files"][0]["sha256"] = "not-a-sha"
    with pytest.raises(ValueError, match="64-character SHA-256"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


@pytest.mark.parametrize("unsafe_path", ["../outside.jpg", "C:/outside.jpg", "/outside.jpg"])
def test_rejects_path_traversal(manifest_case, unsafe_path):
    data_dir, filenames, model, manifest, write = manifest_case
    manifest["test_files"][0]["relative_path"] = unsafe_path
    filenames[0] = unsafe_path
    with pytest.raises(ValueError, match="must not be absolute or escape"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


@pytest.mark.parametrize("unsafe_path", ["C:ship.jpg", "d:relative/path.jpg", "Z:another.jpg"])
def test_rejects_windows_drive_relative_path(manifest_case, unsafe_path):
    data_dir, filenames, model, manifest, write = manifest_case
    manifest["test_files"][0]["relative_path"] = unsafe_path
    filenames[0] = unsafe_path
    with pytest.raises(ValueError, match="must not be absolute or escape"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


def test_rejects_symlinked_dataset_file(manifest_case):
    data_dir, filenames, model, _, write = manifest_case
    original = data_dir / filenames[0]
    target = data_dir / "real-image.jpg"
    target.write_bytes(original.read_bytes())
    original.unlink()
    original.symlink_to(target)
    with pytest.raises(ValueError, match="must not contain symlinks"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


def test_rejects_symlinked_class_directory(manifest_case):
    data_dir, filenames, model, _, write = manifest_case
    original_class = data_dir / "Class0"
    moved_class = data_dir / "Class0-real"
    original_class.rename(moved_class)
    original_class.symlink_to(moved_class, target_is_directory=True)
    with pytest.raises(ValueError, match="must not contain symlinks"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )


def test_rejects_model_hash_mismatch(manifest_case):
    data_dir, filenames, model, manifest, write = manifest_case
    manifest["models"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Model SHA-256"):
        validate_reproducibility_manifest(
            manifest_path=write(), model_path=model, dataset_filenames=filenames, data_dir=data_dir
        )
