"""Fail-closed tests for the official FGSM readiness gate."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from adversarial_ai.audit.official_readiness import check_official_fgsm_readiness


def _contract(tmp_path: Path) -> tuple[Path, dict]:
    data = json.loads(Path("configs/fgsm_official_contract.json").read_text(encoding="utf-8"))
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def test_pending_contract_is_deliberately_not_ready(tmp_path: Path) -> None:
    # Exercise missing binaries in an isolated checkout, not the user's dataset.
    shutil.copytree(Path("configs"), tmp_path / "configs")
    metadata_dir = tmp_path / "results" / "clean"
    metadata_dir.mkdir(parents=True)
    for name in ("cnn_baseline_metadata.json", "mobilenet_metadata.json"):
        shutil.copy2(Path("results") / "clean" / name, metadata_dir / name)
    result = check_official_fgsm_readiness(
        tmp_path, tmp_path / "configs" / "fgsm_official_contract.json"
    )
    assert result["ready"] is False
    assert "experiment approval is pending" in result["blockers"]
    assert any("local model is missing" in blocker for blocker in result["blockers"])
    assert "local 781-image test dataset is missing" in result["blockers"]


def test_contract_rejects_provisional_output_root(tmp_path: Path) -> None:
    path, data = _contract(tmp_path)
    data["outputs"] = {"root": "results/attacks/provisional", "run_id": "run-1"}
    path.write_text(json.dumps(data), encoding="utf-8")
    result = check_official_fgsm_readiness(Path("."), path)
    assert "candidate output root must be results/attacks/official_candidate" in result["blockers"]


def test_contract_rejects_unsafe_or_unapproved_epsilon_values(tmp_path: Path) -> None:
    path, data = _contract(tmp_path)
    data["experiment"]["epsilons"] = [0.01, 0.01]
    path.write_text(json.dumps(data), encoding="utf-8")
    result = check_official_fgsm_readiness(Path("."), path)
    assert any("epsilons" in blocker for blocker in result["blockers"])


def test_contract_rejects_attack_contract_mutation(tmp_path: Path) -> None:
    path, data = _contract(tmp_path)
    data["experiment"]["steps"] = 2
    path.write_text(json.dumps(data), encoding="utf-8")
    result = check_official_fgsm_readiness(Path("."), path)
    assert "experiment.steps violates the FGSM contract" in result["blockers"]


def test_contract_rejects_naive_approval_timestamp(tmp_path: Path) -> None:
    path, data = _contract(tmp_path)
    data["approval"] = {"approved_by": "mentor", "approved_at": "2026-09-11T12:00:00"}
    path.write_text(json.dumps(data), encoding="utf-8")
    result = check_official_fgsm_readiness(Path("."), path)
    assert "approved_at must be an ISO-8601 timestamp" in result["blockers"]
