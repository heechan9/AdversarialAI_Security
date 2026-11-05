"""Read-only paired training configuration/checkpoint audit; no model inference."""
import argparse
import hashlib
import json
from pathlib import Path

from adversarial_ai.training.controls import compare_controls, protocol_hash


def read_json(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError('duplicate JSON key: ' + key)
            out[key] = value
        return out
    def invalid(value):
        raise ValueError('nonfinite JSON value: ' + value)
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_constant=invalid)


def audit(first, second):
    roots = [Path(first).resolve(), Path(second).resolve()]
    if roots[0] == roots[1]:
        raise ValueError('two distinct training directories required')
    reports = []
    for root in roots:
        report = read_json(root / 'training.json')
        for name, key in [('split-audit.json', 'split_audit_sha256'),
                          ('best.keras', 'trained_model_sha256')]:
            path = root / name
            if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != report.get(key):
                raise ValueError('training artifact identity mismatch: ' + name)
        reports.append(report)
    protocol = compare_controls(*reports)
    return dict(result='PAIRED_RECORDED_PROTOCOL_AND_CHECKPOINTS_CONSISTENT',
                comparison_protocol_sha256=protocol_hash(protocol),
                model_sha256={r['training_mode']: r['trained_model_sha256'] for r in reports},
                independent_verification_approval=False, test_evaluation_complete=False,
                limitations=['No inference or execution authentication is performed.',
                             'Matching configuration does not prove identical hardware or stochastic trajectories.',
                             'This is not evidence of an adversarial-training benefit or leakage-free generalization.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('first', type=Path)
    parser.add_argument('second', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.first, args.second), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
