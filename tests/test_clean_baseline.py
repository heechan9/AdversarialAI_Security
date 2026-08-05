import json
from pathlib import Path

import numpy as np
import pytest

from adversarial_ai.data.manifest import build_manifest
from adversarial_ai.evaluation.clean_baseline import (
    build_prediction_frame,
    load_expected_classes,
    sha256_file,
    validate_class_mapping,
)


def test_classes_match_repository_contract():
    classes = load_expected_classes(Path("configs/classes.json"))
    assert len(classes) == 10
    assert classes[0] == "Aircraft Carrier"
    assert classes[-1] == "Tug"


def test_wrong_class_mapping_is_rejected():
    with pytest.raises(ValueError):
        validate_class_mapping({"Tug": 0}, ["Aircraft Carrier", "Tug"])


def test_prediction_csv_contract(tmp_path):
    data_root = tmp_path / "test"
    image = data_root / "A" / "one.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    frame = build_prediction_frame(
        [str(image)], np.array([0]), np.array([[0.75, 0.25]]), ["A", "B"], data_root
    )
    assert frame.loc[0, "relative_path"] == "A/one.jpg"
    assert bool(frame.loc[0, "correct"])
    assert frame.loc[0, "predicted_label"] == "A"


def test_sha256_is_deterministic(tmp_path):
    path = tmp_path / "sample.bin"
    path.write_bytes(b"ship")
    assert sha256_file(path) == sha256_file(path)
    assert len(sha256_file(path)) == 64


def test_manifest_refuses_incomplete_test_set(tmp_path):
    data_root = tmp_path / "test"
    image = data_root / "A" / "one.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    model = tmp_path / "model.h5"
    model.write_bytes(b"model")
    with pytest.raises(ValueError, match="Expected 781"):
        build_manifest(data_root, [model])
