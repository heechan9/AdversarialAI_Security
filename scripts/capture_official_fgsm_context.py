"""Prepare a fresh candidate directory only after the explicit readiness check."""
from __future__ import annotations
import argparse
import json
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from adversarial_ai.audit.official_readiness import (
    CANDIDATE_ROOT, _safe_repo_file, _sha256, check_official_fgsm_readiness,
    validate_official_contract,
)


def capture_context(repo_root: Path, contract_path: Path) -> Path:
    root = repo_root.resolve()
    initial_contract_sha = _sha256(contract_path)
    result = check_official_fgsm_readiness(root, contract_path)
    if not result['ready']:
        raise ValueError('FGSM preparation blocked: ' + '; '.join(result['blockers']))
    contract, blockers = validate_official_contract(root, contract_path)
    if blockers:
        raise ValueError('; '.join(blockers))
    output = _safe_repo_file(root, f"{CANDIDATE_ROOT}/{contract['outputs']['run_id']}")
    if output is None:
        raise ValueError('unsafe candidate path')
    # Resolve required runtime versions before creating any output.
    context = {
        'schema_version': 1,
        'source_commit_sha': contract['source_git_commit'],
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'git_status_short': [],  # readiness requires every tracked file to match HEAD
        'python': platform.python_version(),
        'tensorflow': version('tensorflow'),
        'keras': version('keras'),
        'platform': platform.platform(),
        'output_dir': output.relative_to(root).as_posix(),
        'epsilons': contract['experiment']['epsilons'],
        'contract_sha256': initial_contract_sha,
    }
    raw_contract = contract_path.read_bytes()
    import hashlib
    if hashlib.sha256(raw_contract).hexdigest() != context['contract_sha256']:
        raise ValueError('contract changed during preparation')
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'run_contract.json').open('xb') as f:
        f.write(raw_contract)
    with (output / 'official_execution_context.json').open('x', encoding='utf-8') as f:
        json.dump(context, f, ensure_ascii=False, indent=2, allow_nan=False)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--contract', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(capture_context(Path('.'), args.contract))
    except (ValueError, OSError) as exc:
        print(str(exc))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
