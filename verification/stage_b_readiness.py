"""Fail-closed readiness gate for an independent Stage-B model/image rerun.

This module validates provenance and local assets.  It never loads a model,
runs inference, or writes research results.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

EXPECTED_EPSILONS = [0.0, 0.01, 0.03, 0.05]
SHA256_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> Any:
    def reject_constant(value):
        raise ValueError(f"non-finite JSON number: {value}")

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_unique_object,
        parse_constant=reject_constant,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or "\x00" in value:
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        return None
    candidate = root
    for part in pure.parts:
        candidate = candidate / part
        if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
            return None
    try:
        candidate.resolve(strict=False).relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    return candidate


def _typed_numbers(actual: Any, expected: list[float]) -> bool:
    return (
        isinstance(actual, list)
        and len(actual) == len(expected)
        and all(type(a) in (int, float) and not isinstance(a, bool) and math.isfinite(a) and a == b
                for a, b in zip(actual, expected))
    )


def _validate_contract_schema(contract: Any) -> list[str]:
    blockers: list[str] = []
    expected_top = {
        "schema_version", "status", "verification_kind", "source",
        "dataset", "models", "attack", "comparison", "review", "outputs",
    }
    if not isinstance(contract, dict) or set(contract) != expected_top:
        return ["contract top-level schema mismatch"]
    if contract["schema_version"] != 1 or type(contract["schema_version"]) is not int:
        blockers.append("schema_version must be integer 1")
    if contract["verification_kind"] != "independent_original_model_image_rerun":
        blockers.append("verification_kind mismatch")
    if contract["status"] not in ("draft_assets_required", "ready", "executed"):
        blockers.append("unsupported contract status")

    source = contract["source"]
    if not isinstance(source, dict) or set(source) != {"repository", "commit_sha"}:
        blockers.append("source schema mismatch")

    dataset = contract["dataset"]
    expected_dataset = {"manifest_path", "manifest_sha256", "data_root", "samples"}
    if not isinstance(dataset, dict) or set(dataset) != expected_dataset:
        blockers.append("dataset schema mismatch")
    else:
        if not SHA256_RE.fullmatch(str(dataset["manifest_sha256"])):
            blockers.append("dataset.manifest_sha256 must be lowercase SHA-256")
        if dataset["samples"] != 781 or type(dataset["samples"]) is not int:
            blockers.append("dataset.samples must be integer 781")

    if isinstance(dataset, dict):
        for key, expected in {"manifest_path": "configs/test_manifest.json", "data_root": "data/test"}.items():
            if dataset.get(key) != expected:
                blockers.append(f"dataset.{key} mismatch")
    models = contract["models"]
    if not isinstance(models, list) or not all(isinstance(m, dict) for m in models) or [m.get("id") for m in models] != ["cnn_baseline", "mobilenet"]:
        blockers.append("models must contain cnn_baseline then mobilenet")
    else:
        for model in models:
            if set(model) != {"id", "path", "sha256", "input_shape", "normalization"}:
                blockers.append(f"model schema mismatch: {model.get('id')}")
                continue
            if not SHA256_RE.fullmatch(str(model["sha256"])):
                blockers.append(f"invalid model SHA-256: {model['id']}")
            expected_shape = [128, 128, 3] if model["id"] == "cnn_baseline" else [224, 224, 3]
            if not _typed_numbers(model["input_shape"], expected_shape):
                blockers.append(f"input_shape mismatch: {model['id']}")
            if model["normalization"] != "rescale=1./255":
                blockers.append(f"normalization mismatch: {model['id']}")

    attack = contract["attack"]
    if not isinstance(attack, dict) or set(attack) != {"name", "objective", "steps", "epsilons", "input_range", "clip_range", "norm"}:
        blockers.append("attack schema mismatch")
    else:
        fixed = {
            "name": "fgsm", "objective": "untargeted", "steps": 1,
            "input_range": [0, 1], "clip_range": [0, 1], "norm": "linf",
        }
        for key, expected in fixed.items():
            if attack[key] != expected or type(attack[key]) is not type(expected):
                blockers.append(f"attack.{key} mismatch")
        if not _typed_numbers(attack["epsilons"], EXPECTED_EPSILONS):
            blockers.append("attack.epsilons mismatch")

    comparison = contract["comparison"]
    expected_comparison = {
        "status", "label_match_fraction", "metric_abs_tolerance",
        "probability_abs_tolerance_reference_only", "linf_tolerance",
    }
    if not isinstance(comparison, dict) or set(comparison) != expected_comparison:
        blockers.append("comparison schema mismatch")
    elif comparison["status"] not in ("requires_reviewer_confirmation", "confirmed"):
        blockers.append("comparison.status mismatch")

    if isinstance(comparison, dict) and set(comparison) == expected_comparison:
        for key, expected in {"label_match_fraction": 1.0, "metric_abs_tolerance": 1e-6,
                              "probability_abs_tolerance_reference_only": 1e-5,
                              "linf_tolerance": 1e-6}.items():
            if not _typed_numbers([comparison[key]], [expected]):
                blockers.append(f"comparison.{key} differs from supported tolerance")
    review = contract["review"]
    if not isinstance(review, dict) or set(review) != {"approved_by", "approved_at"}:
        blockers.append("review schema mismatch")

    outputs = contract["outputs"]
    if not isinstance(outputs, dict) or set(outputs) != {"root", "run_id"}:
        blockers.append("outputs schema mismatch")
    elif outputs["root"] != "results/verification/stage_b":
        blockers.append("outputs.root mismatch")
    return blockers


def _validate_manifest(repo_root: Path, contract: dict, verify_assets: bool) -> list[str]:
    blockers: list[str] = []
    dataset = contract["dataset"]
    manifest_path = _safe_path(repo_root, dataset["manifest_path"])
    if manifest_path is None or not manifest_path.is_file():
        return ["canonical dataset manifest is missing or unsafe"]
    if _sha256(manifest_path) != dataset["manifest_sha256"]:
        blockers.append("dataset manifest SHA-256 mismatch")
    try:
        manifest = _load_json(manifest_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return blockers + [f"invalid dataset manifest: {exc}"]
    records = manifest.get("test_files") if isinstance(manifest, dict) else None
    if not isinstance(manifest, dict) or manifest.get("test_samples") != 781 or not isinstance(records, list) or len(records) != 781:
        return blockers + ["dataset manifest must declare exactly 781 images"]
    paths: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != {"relative_path", "label", "sha256"}:
            blockers.append(f"invalid dataset record schema at index {index}")
            continue
        relative = record["relative_path"]
        if _safe_path(repo_root / dataset["data_root"], relative) is None:
            blockers.append(f"unsafe dataset path at index {index}")
        if not isinstance(record["label"], str) or not record["label"]:
            blockers.append(f"invalid dataset label at index {index}")
        if not SHA256_RE.fullmatch(str(record["sha256"])):
            blockers.append(f"invalid dataset SHA-256 at index {index}")
        if isinstance(relative, str):
            paths.append(relative)
    if len(set(paths)) != len(paths):
        blockers.append("dataset manifest contains duplicate paths")
    if blockers or not verify_assets:
        return blockers

    data_root = _safe_path(repo_root, dataset["data_root"])
    if data_root is None or not data_root.is_dir():
        return blockers + ["local 781-image test dataset is missing"]
    for record in records:
        image = _safe_path(data_root, record["relative_path"])
        if image is None or not image.is_file():
            blockers.append(f"missing or unsafe image: {record['relative_path']}")
        elif _sha256(image) != record["sha256"]:
            blockers.append(f"image SHA-256 mismatch: {record['relative_path']}")
    if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)() for p in data_root.rglob("*")):
        blockers.append("local dataset contains symlinks or junctions")
    actual = sorted(
        path.relative_to(data_root).as_posix()
        for path in data_root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )
    if actual != sorted(paths):
        blockers.append("local dataset inventory differs from the locked 781-image manifest")
    return blockers


def check_stage_b_readiness(repo_root: Path, contract_path: Path, *, contract_only: bool = False) -> dict[str, Any]:
    root = repo_root.resolve()
    try:
        contract = _load_json(contract_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return {"ready": False, "contract_valid": False, "blockers": [f"invalid contract: {exc}"]}
    blockers = _validate_contract_schema(contract)
    if blockers:
        return {"ready": False, "contract_valid": False, "blockers": blockers}
    try:
        blockers.extend(_validate_manifest(root, contract, verify_assets=not contract_only))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        blockers.append(f"unreadable or malformed manifest/assets: {exc}")
    if contract_only:
        return {"ready": False, "contract_valid": not blockers, "blockers": blockers,
                "note": "Contract-only validation does not prove Stage-B execution readiness."}

    if contract["status"] != "ready":
        blockers.append("Stage-B contract status is not ready")
    if contract["comparison"]["status"] != "confirmed":
        blockers.append("comparison tolerances require reviewer confirmation")
    review = contract["review"]
    if not all(isinstance(review[key], str) and review[key].strip() for key in review):
        blockers.append("review approval record is incomplete")
    else:
        try:
            approved_at = datetime.fromisoformat(review["approved_at"].replace("Z", "+00:00"))
            if approved_at.utcoffset() is None or approved_at > datetime.now(timezone.utc):
                raise ValueError
        except ValueError:
            blockers.append("review.approved_at must be a non-future ISO-8601 timestamp")
    source_sha = contract["source"]["commit_sha"]
    if not isinstance(source_sha, str) or not COMMIT_RE.fullmatch(source_sha):
        blockers.append("source.commit_sha must be a full lowercase commit SHA")
    else:
        try:
            actual_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True,
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            dirty = subprocess.run(
                ["git", "diff", "--name-only", "HEAD", "--"], cwd=root, check=True,
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
            if dirty:
                blockers.append("tracked checkout differs from source commit")
            if actual_sha != source_sha:
                blockers.append("source.commit_sha differs from checked-out HEAD")
        except (OSError, subprocess.SubprocessError):
            blockers.append("unable to resolve checked-out Git commit")
    for model in contract["models"]:
        path = _safe_path(root, model["path"])
        if path is None or not path.is_file():
            blockers.append(f"local model is missing or unsafe: {model['path']}")
        elif _sha256(path) != model["sha256"]:
            blockers.append(f"model SHA-256 mismatch: {model['path']}")
    run_id = contract["outputs"]["run_id"]
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", run_id):
        blockers.append("outputs.run_id must be a safe non-empty identifier")
    else:
        output = _safe_path(root, f"{contract['outputs']['root']}/{run_id}")
        if output is None:
            blockers.append("Stage-B output path is unsafe")
        elif output.exists():
            blockers.append("Stage-B output path already exists; overwrite is forbidden")
    return {"ready": not blockers, "contract_valid": True, "blockers": blockers}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--contract", type=Path, default=Path("configs/stage_b_verification_contract.json"))
    parser.add_argument("--contract-only", action="store_true")
    args = parser.parse_args(argv)
    result = check_stage_b_readiness(args.repo_root, args.contract, contract_only=args.contract_only)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.contract_only:
        return 0 if result["contract_valid"] else 2
    return 0 if result["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

