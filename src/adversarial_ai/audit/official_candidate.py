"""Fail-closed audit for an isolated official FGSM candidate run."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from adversarial_ai.audit.clean import audit_clean_evaluation
from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.fgsm import EXPECTED_EPSILONS, audit_fgsm_results
from adversarial_ai.audit.manifest_models import audit_manifest, audit_models
from adversarial_ai.audit.runner import get_git_commit_sha
from adversarial_ai.audit.official_readiness import (
    CANDIDATE_ROOT, _safe_repo_file, _sha256, _same_typed_value, load_strict_json, validate_official_contract,
)


MODEL_SPECS = {
    "cnn": {
        "model_path": "models/cnn_baseline.h5",
        "input_size": [128, 128, 3],
        "clean_eval": "cnn_baseline_eval.csv",
        "clean_summary": "cnn_baseline_summary.json",
    },
    "mobilenet": {
        "model_path": "models/mobilenet_finetuned.h5",
        "input_size": [224, 224, 3],
        "clean_eval": "mobilenet_eval.csv",
        "clean_summary": "mobilenet_summary.json",
    },
}

METADATA_FIELDS = {
    "executed_at_utc",
    "python",
    "tensorflow",
    "keras",
    "model",
    "model_path",
    "model_sha256",
    "manifest_path",
    "input_size",
    "input_range",
    "norm",
    "attack",
    "loss",
    "from_logits",
    "epsilons",
    "asr_denominator",
}

CONTEXT_FIELDS = {
    "contract_sha256",
    "schema_version",
    "source_commit_sha",
    "captured_at_utc",
    "git_status_short",
    "python",
    "tensorflow",
    "keras",
    "platform",
    "output_dir",
    "epsilons",
}


def _load_exact_json(path: Path, fields: set[str], context: str) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise AuditError(f"{context} missing or unsafe: {path}")
    try:
        value = load_strict_json(path)
    except Exception as exc:
        raise AuditError(f"Failed to parse {context}: {path}", {"error": str(exc)}) from exc
    if not isinstance(value, dict) or set(value) != fields:
        raise AuditError(
            f"{context} schema mismatch: {path}",
            {"expected": sorted(fields), "actual": sorted(value) if isinstance(value, dict) else None},
        )
    return value


def _parse_utc(value: Any, context: str) -> dt.datetime:
    if not isinstance(value, str):
        raise AuditError(f"{context} must be an ISO-8601 UTC string")
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise AuditError(f"{context} is not valid ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise AuditError(f"{context} must include a UTC offset")
    return parsed


def _expected_root_files() -> set[str]:
    names = {"official_execution_context.json", "run_contract.json"}
    for model in MODEL_SPECS:
        names.update({f"fgsm_{model}.csv", f"fgsm_{model}_metadata.json"})
        for epsilon in EXPECTED_EPSILONS:
            token = "0" if epsilon == 0.0 else str(epsilon)
            stem = f"fgsm_{model}_eps_{token}"
            names.update(
                {
                    f"{stem}_samples.csv",
                    f"{stem}_report.json",
                    f"{stem}_confusion_matrix.csv",
                    f"{stem}_confusion_matrix.png",
                }
            )
    return names


def audit_official_candidate(
    repo_root: Path = Path("."),
    candidate_dir: Path | None = None,
) -> dict[str, Any]:
    """Audit a complete candidate without promoting or rewriting any artifact."""
    root = repo_root.resolve()
    if candidate_dir is None:
        raise AuditError("Select one explicit candidate run directory")
    candidate_path = candidate_dir if candidate_dir.is_absolute() else root / candidate_dir
    try:
        relative = candidate_path.absolute().relative_to(root).as_posix()
    except ValueError as exc:
        raise AuditError("Official candidate directory is outside the checkout") from exc
    candidate = _safe_repo_file(root, relative)
    if candidate is None or not candidate.is_dir():
        raise AuditError("Official candidate directory is missing or unsafe")
    if candidate.parent != root / CANDIDATE_ROOT:
        raise AuditError("Official candidate must be a named run under the candidate root")
    run_contract_path = candidate / "run_contract.json"
    contract, blockers = validate_official_contract(root, run_contract_path)
    if blockers:
        raise AuditError("Official candidate contract invalid: " + "; ".join(blockers))
    if contract['outputs']['run_id'] != candidate.name:
        raise AuditError("Official candidate run_id differs from its directory")

    root_entries = list(candidate.iterdir())
    actual_root_files = {path.name for path in root_entries if path.is_file()}
    if actual_root_files != _expected_root_files():
        raise AuditError(
            "Official candidate root file inventory mismatch",
            {
                "missing": sorted(_expected_root_files() - actual_root_files),
                "unexpected": sorted(actual_root_files - _expected_root_files()),
            },
        )
    unexpected_entries = {
        path.name
        for path in root_entries
        if path.name != "samples" and (not path.is_file() or path.is_symlink())
    }
    if unexpected_entries:
        raise AuditError(
            "Official candidate root contains an unsafe or unexpected entry",
            {"unexpected": sorted(unexpected_entries)},
        )
    sample_dir = candidate / "samples"
    if not sample_dir.is_dir() or sample_dir.is_symlink():
        raise AuditError("Official candidate samples directory is missing or unsafe")
    if any(
        path.is_symlink() or not path.is_file() or path.suffix.lower() != ".png"
        for path in sample_dir.iterdir()
    ):
        raise AuditError("Official candidate samples directory contains an unsafe or unexpected entry")

    context = _load_exact_json(
        candidate / "official_execution_context.json", CONTEXT_FIELDS, "official execution context"
    )
    if type(context["schema_version"]) is not int or context["schema_version"] != 1:
        raise AuditError("Unsupported official execution context schema version")
    source_sha = context["source_commit_sha"]
    if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40,64}", source_sha):
        raise AuditError("Official execution source_commit_sha is invalid")
    if source_sha != get_git_commit_sha(root):
        raise AuditError("Official execution commit differs from the audited checkout")
    captured_at = _parse_utc(context["captured_at_utc"], "official context captured_at_utc")
    if context["output_dir"] != candidate.relative_to(root).as_posix():
        raise AuditError("Official execution context output_dir is not the isolated candidate path")
    if context["contract_sha256"] != _sha256(run_contract_path):
        raise AuditError("Official candidate contract SHA-256 mismatch")
    if not _same_typed_value(context["epsilons"], contract["experiment"]["epsilons"]):
        raise AuditError("Official execution context epsilon sweep differs from the contract")
    for key in ("python", "tensorflow", "keras", "platform"):
        if not isinstance(context[key], str) or not context[key].strip():
            raise AuditError(f"Official execution context {key} must be non-empty")
    if not isinstance(context["git_status_short"], list) or not all(
        isinstance(row, str) for row in context["git_status_short"]
    ):
        raise AuditError("Official execution context git_status_short must be a string list")

    if context["git_status_short"]:
        raise AuditError("Official execution context reports a dirty tracked checkout")

    manifest = audit_manifest(
        root / "configs" / "test_manifest.json",
        data_dir=root / "data" / "test" if (root / "data" / "test").is_dir() else None,
    )
    clean_dir = root / "results" / "clean"
    audited: dict[str, Any] = {}
    metadata_paths: list[Path] = []
    for model, spec in MODEL_SPECS.items():
        clean = audit_clean_evaluation(
            clean_dir / spec["clean_eval"],
            summary_json_path=clean_dir / spec["clean_summary"],
            expected_relative_paths=manifest["relative_paths"],
            expected_true_labels=manifest["true_labels"],
        )
        audited[model] = audit_fgsm_results(
            candidate,
            model,
            clean["correct_count"],
            clean["clean_correct_mask"],
            clean["relative_paths"],
            clean["true_labels"],
            clean["predicted_labels"],
        )

        metadata_path = candidate / f"fgsm_{model}_metadata.json"
        metadata_paths.append(metadata_path)
        metadata = _load_exact_json(metadata_path, METADATA_FIELDS, f"{model} FGSM metadata")
        if metadata["model"] != model or metadata["model_path"] != spec["model_path"]:
            raise AuditError(f"Official {model} metadata identifies the wrong model")
        if metadata["manifest_path"] != "configs/test_manifest.json":
            raise AuditError(f"Official {model} metadata identifies the wrong manifest")
        if metadata["input_size"] != spec["input_size"] or metadata["input_range"] != [0, 1]:
            raise AuditError(f"Official {model} metadata input contract mismatch")
        if not _same_typed_value(metadata["epsilons"], contract["experiment"]["epsilons"]):
            raise AuditError(f"Official {model} metadata epsilon sweep mismatch")
        expected_literals = {
            "norm": "L-infinity",
            "attack": "untargeted FGSM, exactly one step",
            "loss": "categorical_crossentropy",
            "asr_denominator": "clean-correct samples only",
        }
        if any(metadata[key] != value for key, value in expected_literals.items()):
            raise AuditError(f"Official {model} metadata attack contract mismatch")
        if not isinstance(metadata["from_logits"], bool):
            raise AuditError(f"Official {model} metadata from_logits must be boolean")
        for key in ("python", "tensorflow", "keras"):
            if metadata[key] != context[key]:
                raise AuditError(f"Official {model} metadata {key} differs from execution context")
        executed_at = _parse_utc(metadata["executed_at_utc"], f"{model} executed_at_utc")
        if executed_at < captured_at or executed_at > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
            raise AuditError(f"Official {model} execution timestamp is outside the recorded run window")

    model_integrity = audit_models(manifest["manifest_models"], metadata_paths, repo_root=root)
    return {
        "status": "PASSED",
        "source_commit_sha": source_sha,
        "epsilons": EXPECTED_EPSILONS,
        "models": audited,
        "images_verified": manifest["verified_image_files"],
        "model_binaries_verified": all(m["disk_file_present"] for m in model_integrity.values()),
        "promoted_to_official": False,
        "claim_boundary": "Artifact consistency only; approval authenticity and actual execution are not certified",

    }
