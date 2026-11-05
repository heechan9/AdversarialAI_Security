"""Export the real stdlib auditor's public output, with portable repository paths."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from verification.fgsm_run_audit import audit

SOURCE_COMMIT = '4cf62f8ee164dcdfb15403d17474eb06fe814cef'
OUTPUT = ROOT / 'web/maris/public/evidence/fgsm-run-audit.json'


def snapshot():
    relative = 'results/attacks/provisional'
    report = audit([ROOT / relative], ROOT)
    for condition in report['conditions']:
        condition['file'] = Path(condition['file']).relative_to(ROOT).as_posix()
        # This view displays coverage and restart requirements, not metrics.
        # Omitting unused reductions also avoids Python-version float-sum drift.
        condition.pop('metrics')
    for invocation in report['invocations']:
        invocation['directory'] = Path(invocation['directory']).relative_to(ROOT).as_posix()
    code = ['configs/test_manifest.json', 'configs/classes.json',
            'verification/fgsm_run_audit.py', 'web/maris/scripts/export-fgsm-audit.py']
    return dict(schema='maris-fgsm-audit/v1', inference_performed=False,
                evidence_source_commit=SOURCE_COMMIT, report=report,
                source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in code})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    data = (json.dumps(snapshot(), ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != data:
            parser.exit(1, 'FGSM public audit snapshot is missing or stale; regenerate with this exporter.\n')
        print('PASS: FGSM public snapshot matches the saved-output auditor; no inference.')
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_bytes(data)
        print(f'Exported {len(data):,} bytes of public FGSM saved-output audit.')


if __name__ == '__main__':
    main()
