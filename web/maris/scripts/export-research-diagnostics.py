"""Deterministic public diagnostics from saved evidence; never runs a model."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from verification.matched_cnn_diagnostics import build_report, CONDITIONS
from verification.discrepancy_triage import build

OUTPUT = ROOT / 'web/maris/public/evidence/research-diagnostics.json'


def snapshot():
    matched = {c: build_report(ROOT / 'results/extensions/matched_cnn_20261024', c, outcome='all')
               for c in CONDITIONS}
    triage = build(ROOT)
    # Public evidence identifiers and predictions only. Images and model binaries
    # are neither read nor copied. Source CSV hashes in triage are declarations.
    code = ['verification/matched_cnn_diagnostics.py', 'verification/matched_cnn_saved_audit.py',
            'verification/discrepancy_triage.py', 'verification/issue_lifecycle.py',
            'verification/status_registry.py', 'web/maris/scripts/export-research-diagnostics.py']
    return dict(schema='maris-research-diagnostics/v1', inference_performed=False,
                matched=matched, triage=triage,
                generator_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in code})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Reject a missing or stale public snapshot')
    args = parser.parse_args()
    data = (json.dumps(snapshot(), ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != data:
            parser.exit(1, 'Research diagnostics snapshot is missing or stale.\n')
        print('PASS: public diagnostics match audited saved evidence and current lifecycle gates.')
    else:
        OUTPUT.write_bytes(data)
        print(f'Exported saved diagnostics ({len(data):,} bytes); no model inference.')


if __name__ == '__main__':
    main()
