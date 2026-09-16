"""Read-only checks for an isolated FGSM candidate, never an approval authority."""
from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.fgsm import EXPECTED_EPSILONS
from adversarial_ai.audit.manifest_models import audit_manifest
from adversarial_ai.audit.runner import get_git_commit_sha

CANDIDATE_ROOT = 'results/attacks/official_candidate'


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f'duplicate JSON key: {key}')
        obj[key] = value
    return obj


def load_strict_json(path: Path) -> Any:
    def reject_constant(value):
        raise ValueError(f'non-finite JSON number: {value}')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_unique_object,
                      parse_constant=reject_constant)


def _safe_repo_file(repo_root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or '\x00' in value:
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(p in {'', '.', '..'} for p in value.split('/')):
        return None
    candidate = repo_root
    for part in pure.parts:
        candidate = candidate / part
        if candidate.is_symlink() or getattr(candidate, 'is_junction', lambda: False)():
            return None
    try:
        candidate.resolve(strict=False).relative_to(repo_root)
    except (ValueError, OSError):
        return None
    return candidate


def _same_typed_value(actual, expected):
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            _same_typed_value(a, b) for a, b in zip(actual, expected))
    if type(expected) in (int, float):
        try:
            return type(actual) in (int, float) and math.isfinite(actual) and actual == expected
        except OverflowError:
            return False
    return type(actual) is type(expected) and actual == expected


def validate_official_contract(repo_root: Path, contract_path: Path) -> tuple[dict, list[str]]:
    """Check an explicit run contract without requiring an empty output directory.

    Reused before execution and when auditing the completed candidate. A string
    approval record is checked for completeness, not authenticated by this code.
    """
    repo_root = repo_root.resolve()
    blockers = []
    try:
        contract = load_strict_json(contract_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return {}, [f'invalid contract: {exc}']
    expected_top = {'schema_version', 'status', 'approval', 'source_git_commit', 'experiment', 'outputs'}
    if not isinstance(contract, dict) or set(contract) != expected_top:
        return {}, ['contract top-level schema mismatch']
    if type(contract['schema_version']) is not int or contract['schema_version'] != 1:
        blockers.append('schema_version must be integer 1')
    if contract['status'] != 'approved':
        blockers.append('experiment approval is pending')
    approval = contract['approval']
    if not isinstance(approval, dict) or set(approval) != {'approved_by', 'approved_at'}:
        blockers.append('approval schema mismatch')
    elif not all(isinstance(v, str) and v.strip() for v in approval.values()):
        blockers.append('approved_by and approved_at are required')
    else:
        try:
            approved_at = datetime.fromisoformat(approval['approved_at'].replace('Z', '+00:00'))
            if approved_at.utcoffset() is None:
                raise ValueError
            if approved_at > datetime.now(timezone.utc):
                blockers.append('approved_at must not be in the future')
        except ValueError:
            blockers.append('approved_at must be an ISO-8601 timestamp')
    commit = contract['source_git_commit']
    if not isinstance(commit, str) or not re.fullmatch(r'[0-9a-f]{40}', commit):
        blockers.append('source_git_commit must be a full lowercase commit SHA')
    else:
        try:
            if commit != get_git_commit_sha(repo_root):
                blockers.append('source_git_commit must equal the checked-out commit')
        except AuditError:
            blockers.append('unable to resolve the checked-out Git commit')
    fixed = {'attack': 'fgsm', 'objective': 'untargeted', 'labels': 'true', 'steps': 1,
             'input_range': [0, 1], 'clip_range': [0, 1], 'norm': 'linf',
             'linf_tolerance': 1e-6, 'asr_denominator': 'clean_correct'}
    experiment = contract['experiment']
    if not isinstance(experiment, dict) or set(experiment) != set(fixed) | {'epsilons'}:
        blockers.append('experiment schema mismatch')
    else:
        for key, expected in fixed.items():
            if not _same_typed_value(experiment[key], expected):
                blockers.append(f'experiment.{key} violates the FGSM contract')
        eps = experiment['epsilons']
        # Reuse the existing audited sweep. Supporting a different sweep needs a
        # separate contract/auditor review; merely typing new numbers cannot enable it.
        if not _same_typed_value(eps, list(EXPECTED_EPSILONS)):
            blockers.append('approved epsilons must equal the currently supported audited sweep')
    outputs = contract['outputs']
    if not isinstance(outputs, dict) or set(outputs) != {'root', 'run_id'}:
        blockers.append('outputs schema mismatch')
    else:
        if outputs['root'] != CANDIDATE_ROOT:
            blockers.append(f'candidate output root must be {CANDIDATE_ROOT}')
        run_id = outputs['run_id']
        reserved = {'con', 'prn', 'aux', 'nul'} | {f'{p}{i}' for p in ('com', 'lpt') for i in range(1,10)}
        if (not isinstance(run_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', run_id)
                or run_id in reserved):
            blockers.append('run_id must be a non-empty safe identifier')
        elif _safe_repo_file(repo_root, f'{CANDIDATE_ROOT}/{run_id}') is None:
            blockers.append('candidate output directory is unsafe')
    return contract, blockers


def check_official_fgsm_readiness(repo_root: Path, contract_path: Path) -> dict[str, Any]:
    """Require a reviewed checkout, actual binaries and a fresh candidate path."""
    repo_root = repo_root.resolve()
    contract, blockers = validate_official_contract(repo_root, contract_path)
    if not contract:
        return {'ready': False, 'blockers': blockers}
    if contract['status'] == 'approved' and contract_path.resolve().is_relative_to(repo_root):
        blockers.append('approved run contract must be outside the checkout to avoid self-referential source SHA')
    outputs = contract.get('outputs')
    if isinstance(outputs, dict) and isinstance(outputs.get('run_id'), str):
        candidate = _safe_repo_file(repo_root, f"{CANDIDATE_ROOT}/{outputs['run_id']}")
        if candidate is not None and candidate.exists():
            blockers.append('candidate output directory already exists; overwrite is forbidden')
    try:
        dirty = subprocess.run(['git', 'diff', '--name-only', 'HEAD', '--'], cwd=repo_root,
                               check=True, capture_output=True, text=True, timeout=5).stdout.strip()
        if dirty:
            blockers.append('tracked checkout files differ from source commit')
    except (OSError, subprocess.SubprocessError):
        blockers.append('unable to check tracked checkout changes')
    manifest_models = {}
    data_dir = _safe_repo_file(repo_root, 'data/test')
    present = data_dir is not None and data_dir.is_dir()
    if not present:
        blockers.append('local 781-image test dataset is missing')
    try:
        manifest_path = _safe_repo_file(repo_root, 'configs/test_manifest.json')
        if manifest_path is None:
            raise AuditError('unsafe manifest path')
        manifest = audit_manifest(manifest_path, data_dir=data_dir if present else None)
        manifest_models = manifest['manifest_models']
    except AuditError as exc:
        blockers.append(f'canonical test manifest or image SHA-256 verification failed: {exc}')
    for name in ('cnn_baseline_metadata.json', 'mobilenet_metadata.json'):
        try:
            path = _safe_repo_file(repo_root, f'results/clean/{name}')
            if path is None:
                raise ValueError('unsafe metadata path')
            meta = load_strict_json(path)
            if not isinstance(meta, dict):
                raise ValueError('metadata root must be an object')
            model_path = _safe_repo_file(repo_root, meta.get('model_path'))
            if model_path is None:
                blockers.append(f'unsafe local model path in metadata: {name}')
            elif not model_path.is_file():
                blockers.append(f"local model is missing: {meta['model_path']}")
            elif _sha256(model_path) != meta['model_sha256']:
                blockers.append(f"local model SHA-256 mismatch: {meta['model_path']}")
            elif manifest_models.get(meta['model_path']) != meta['model_sha256']:
                blockers.append(f"model SHA-256 disagrees with manifest: {meta['model_path']}")
        except (OSError, KeyError, UnicodeError, ValueError):
            blockers.append(f'invalid Clean metadata: {name}')
    return {'ready': not blockers, 'blockers': blockers}
