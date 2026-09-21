import hashlib
import json
from pathlib import Path

from verification.stage_b_readiness import check_stage_b_readiness


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _case(tmp_path: Path):
    root = tmp_path / "repo"
    (root / "configs").mkdir(parents=True)
    (root / "data" / "test").mkdir(parents=True)
    records = []
    for index in range(781):
        relative = f"Class{index % 10}/image-{index}.jpg"
        payload = f"image-{index}".encode()
        image = root / "data" / "test" / relative
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(payload)
        records.append({"relative_path": relative, "label": f"Class{index % 10}", "sha256": _sha(payload)})
    manifest = {"test_samples": 781, "test_files": records}
    manifest_path = root / "configs" / "test_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    model_specs = []
    for model_id, filename, shape in (
        ("cnn_baseline", "cnn_baseline.h5", [128, 128, 3]),
        ("mobilenet", "mobilenet_finetuned.h5", [224, 224, 3]),
    ):
        model = root / "models" / filename
        model.parent.mkdir(exist_ok=True)
        payload = model_id.encode()
        model.write_bytes(payload)
        model_specs.append({"id": model_id, "path": f"models/{filename}", "sha256": _sha(payload),
                            "input_shape": shape, "normalization": "rescale=1./255"})
    contract = {
        "schema_version": 1,
        "status": "draft_assets_required",
        "verification_kind": "independent_original_model_image_rerun",
        "source": {"repository": "https://example.invalid/repo", "commit_sha": None},
        "dataset": {"manifest_path": "configs/test_manifest.json", "manifest_sha256": _sha(manifest_path.read_bytes()),
                    "data_root": "data/test", "samples": 781},
        "models": model_specs,
        "attack": {"name": "fgsm", "objective": "untargeted", "steps": 1,
                   "epsilons": [0.0, 0.01, 0.03, 0.05], "input_range": [0, 1],
                   "clip_range": [0, 1], "norm": "linf"},
        "comparison": {"status": "requires_reviewer_confirmation", "label_match_fraction": 1.0,
                       "metric_abs_tolerance": 1e-6, "probability_abs_tolerance_reference_only": 1e-5,
                       "linf_tolerance": 1e-6},
        "review": {"approved_by": None, "approved_at": None},
        "outputs": {"root": "results/verification/stage_b", "run_id": None},
    }
    contract_path = root / "configs" / "stage_b_verification_contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    return root, contract_path, contract, manifest_path


def test_contract_only_accepts_locked_manifest(tmp_path):
    root, contract_path, _, _ = _case(tmp_path)
    result = check_stage_b_readiness(root, contract_path, contract_only=True)
    assert result["contract_valid"] is True
    assert result["ready"] is False
    assert result["blockers"] == []


def test_default_fails_closed_while_review_and_commit_are_missing(tmp_path):
    root, contract_path, _, _ = _case(tmp_path)
    result = check_stage_b_readiness(root, contract_path)
    assert result["ready"] is False
    assert "Stage-B contract status is not ready" in result["blockers"]
    assert "comparison tolerances require reviewer confirmation" in result["blockers"]
    assert "review approval record is incomplete" in result["blockers"]
    assert "source.commit_sha must be a full lowercase commit SHA" in result["blockers"]


def test_manifest_mutation_fails_contract_only(tmp_path):
    root, contract_path, _, manifest_path = _case(tmp_path)
    manifest_path.write_text(manifest_path.read_text() + " ", encoding="utf-8")
    result = check_stage_b_readiness(root, contract_path, contract_only=True)
    assert result["contract_valid"] is False
    assert "dataset manifest SHA-256 mismatch" in result["blockers"]


def test_image_mutation_fails_actual_readiness(tmp_path):
    root, contract_path, contract, _ = _case(tmp_path)
    image = root / "data" / "test" / "Class0" / "image-0.jpg"
    image.write_bytes(b"tampered")
    result = check_stage_b_readiness(root, contract_path)
    assert any("image SHA-256 mismatch" in item for item in result["blockers"])


def test_model_mutation_fails_actual_readiness(tmp_path):
    root, contract_path, contract, _ = _case(tmp_path)
    (root / contract["models"][0]["path"]).write_bytes(b"tampered")
    result = check_stage_b_readiness(root, contract_path)
    assert any("model SHA-256 mismatch" in item for item in result["blockers"])


def test_extra_dataset_file_fails_inventory(tmp_path):
    root, contract_path, _, _ = _case(tmp_path)
    (root / "data" / "test" / "extra.jpg").write_bytes(b"extra")
    result = check_stage_b_readiness(root, contract_path)
    assert "local dataset inventory differs from the locked 781-image manifest" in result["blockers"]


def test_duplicate_json_key_is_rejected(tmp_path):
    root, contract_path, _, _ = _case(tmp_path)
    contract_path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    result = check_stage_b_readiness(root, contract_path, contract_only=True)
    assert result["contract_valid"] is False
    assert "duplicate JSON key" in result["blockers"][0]


def test_paper_scope_and_formal_run_approval_are_not_conflated():
    official = json.loads(Path("configs/fgsm_official_contract.json").read_text(encoding="utf-8"))
    experiment = Path("configs/experiment.yaml").read_text(encoding="utf-8")
    assert official["status"] == "pending_team_confirmation"
    assert official["approval"] == {"approved_by": None, "approved_at": None}
    assert official["experiment"]["epsilons"] == [0.0, 0.01, 0.03, 0.05]
    assert 'status: "confirmed"' in experiment
    assert 'independent_model_and_image_rerun: "not_completed"' in experiment



import pytest

@pytest.mark.parametrize("value", [-1, True, "1e-6", 1, None])
def test_invalid_tolerance_rejected(tmp_path, value):
    root, path, contract, _ = _case(tmp_path)
    contract["comparison"]["metric_abs_tolerance"] = value
    path.write_text(json.dumps(contract))
    assert not check_stage_b_readiness(root, path, contract_only=True)["contract_valid"]

@pytest.mark.parametrize("value", [[], None, 42, {"test_samples": 781, "test_files": [None]*781}])
def test_malformed_manifest_returns_failure(tmp_path, value):
    root, path, contract, manifest = _case(tmp_path)
    manifest.write_text(json.dumps(value))
    contract["dataset"]["manifest_sha256"] = _sha(manifest.read_bytes())
    path.write_text(json.dumps(contract))
    assert check_stage_b_readiness(root, path)["ready"] is False


def test_extra_symlink_rejected(tmp_path):
    root, path, _, _ = _case(tmp_path)
    (root / "data/test/extra.jpg").symlink_to(root / "data/test/Class0/image-0.jpg")
    assert "local dataset contains symlinks or junctions" in check_stage_b_readiness(root, path)["blockers"]
