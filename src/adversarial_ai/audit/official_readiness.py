"""Fail-closed readiness checks for a future official FGSM run."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.manifest_models import audit_manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_repo_file(repo_root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        return None
    candidate = repo_root
    for part in pure.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            return None
    try:
        candidate.resolve(strict=False).relative_to(repo_root)
    except ValueError:
        return None
    return candidate


def check_official_fgsm_readiness(repo_root: Path, contract_path: Path) -> dict[str, Any]:
    """Return every blocking condition; this function never executes an experiment."""

    repo_root = repo_root.resolve()
    blockers: list[str] = []
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {"ready": False, "blockers": [f"invalid contract: {exc}"]}

    expected_top = {"schema_version", "status", "approval", "source_git_commit", "experiment", "outputs"}
    if not isinstance(contract, dict) or set(contract) != expected_top:
        return {"ready": False, "blockers": ["contract top-level schema mismatch"]}
    if contract.get("schema_version") != 1:
        blockers.append("schema_version must be 1")
    if contract.get("status") != "approved":
        blockers.append("mentor approval is pending")

    approval = contract.get("approval")
    if not isinstance(approval, dict) or set(approval) != {"approved_by", "approved_at"}:
        blockers.append("approval schema mismatch")
    elif not all(isinstance(approval.get(key), str) and approval[key].strip() for key in approval):
        blockers.append("approved_by and approved_at are required")
    else:
        try:
            approved_at = datetime.fromisoformat(approval["approved_at"].replace("Z", "+00:00"))
            if approved_at.utcoffset() is None:
                raise ValueError
        except ValueError:
            blockers.append("approved_at must be an ISO-8601 timestamp")

    commit = contract.get("source_git_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        blockers.append("source_git_commit must be a full lowercase commit SHA")
    else:
        try:
            current_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True,
                capture_output=True, text=True,
            ).stdout.strip()
            if commit != current_commit:
                blockers.append("source_git_commit must equal the checked-out commit")
        except (OSError, subprocess.CalledProcessError):
            blockers.append("unable to resolve the checked-out Git commit")

    experiment = contract.get("experiment")
    expected_experiment = {
        "attack", "objective", "labels", "steps", "input_range", "clip_range",
        "norm", "linf_tolerance", "asr_denominator", "epsilons",
    }
    fixed = {
        "attack": "fgsm", "objective": "untargeted", "labels": "true", "steps": 1,
        "input_range": [0, 1], "clip_range": [0, 1], "norm": "linf",
        "linf_tolerance": 1e-6, "asr_denominator": "clean_correct",
    }
    if not isinstance(experiment, dict) or set(experiment) != expected_experiment:
        blockers.append("experiment schema mismatch")
    else:
        for key, expected in fixed.items():
            if experiment.get(key) != expected:
                blockers.append(f"experiment.{key} violates the FGSM contract")
        epsilons = experiment.get("epsilons")
        valid_eps = (
            isinstance(epsilons, list)
            and len(epsilons) >= 2
            and all(isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 for value in epsilons)
            and 0 in epsilons
            and len(epsilons) == len(set(epsilons))
            and epsilons == sorted(epsilons)
        )
        if not valid_eps:
            blockers.append("mentor-approved epsilons must be sorted, unique, finite, nonnegative, and include 0")

    outputs = contract.get("outputs")
    if not isinstance(outputs, dict) or set(outputs) != {"root", "run_id"}:
        blockers.append("outputs schema mismatch")
    else:
        root = outputs.get("root")
        run_id = outputs.get("run_id")
        if root != "results/attacks/official":
            blockers.append("official output root must be results/attacks/official")
        if not isinstance(run_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", run_id):
            blockers.append("run_id must be a non-empty safe identifier")
        elif (repo_root / str(root) / run_id).exists():
            blockers.append("official output directory already exists; overwrite is forbidden")

    manifest_path = repo_root / "configs" / "test_manifest.json"
    manifest_models: dict[str, str] = {}
    data_dir = repo_root / "data" / "test"
    if not data_dir.is_dir():
        blockers.append("local 781-image test dataset is missing")
    try:
        manifest = audit_manifest(manifest_path, data_dir=data_dir if data_dir.is_dir() else None)
        manifest_models = manifest["manifest_models"]
    except AuditError as exc:
        blockers.append(f"canonical test manifest or image SHA-256 verification failed: {exc}")
    for metadata_name in ("cnn_baseline_metadata.json", "mobilenet_metadata.json"):
        metadata_path = repo_root / "results" / "clean" / metadata_name
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            model_path = _safe_repo_file(repo_root, metadata.get("model_path"))
            if model_path is None:
                blockers.append(f"unsafe local model path in metadata: {metadata_name}")
            elif not model_path.is_file():
                blockers.append(f"local model is missing: {metadata['model_path']}")
            elif _sha256(model_path) != metadata["model_sha256"]:
                blockers.append(f"local model SHA-256 mismatch: {metadata['model_path']}")
            elif manifest_models.get(metadata["model_path"]) != metadata["model_sha256"]:
                blockers.append(f"model SHA-256 disagrees with manifest: {metadata['model_path']}")
        except (OSError, KeyError, UnicodeDecodeError, json.JSONDecodeError):
            blockers.append(f"invalid Clean metadata: {metadata_name}")

    return {"ready": not blockers, "blockers": blockers}
