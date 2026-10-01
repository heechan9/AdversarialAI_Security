"""Capture and audit completed conditions without changing a running experiment."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

from verification.iterative_result_audit import audit, read_json


def capture(source, destination, repo_root):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Capture the report once. A runner may append conditions after this read.
    # Only CSVs referenced by these exact report bytes belong to this snapshot.
    report_bytes = (source / 'run.json').read_bytes()
    with tempfile.TemporaryDirectory(prefix='.snapshot-', dir=destination.parent) as temporary:
        stage = Path(temporary) / 'capture'
        stage.mkdir()
        (stage / 'run.json').write_bytes(report_bytes)
        report = read_json(stage / 'run.json')
        for condition in report['conditions']:
            name = condition['csv']
            if Path(name).name != name or '/' in name or '\\' in name or not name.endswith('.csv'):
                raise ValueError('unsafe CSV name')
            original = source / name
            if original.is_symlink():
                raise ValueError('CSV symlink forbidden')
            (stage / name).write_bytes(original.read_bytes())
        checked = audit(stage, repo_root)
        (stage / 'audit.json').write_text(json.dumps(checked, indent=2) + '\n')
        lines = [
            '# Follow-up experiment snapshot', '',
            f"Coverage: {checked['checked_conditions']}/{checked['expected_conditions']} conditions.",
            f"Audit: **{checked['result']}**. Captured execution status: {report['status']}.",
            'This is a fixed snapshot, not live monitoring or independent verification approval.',
            'Accuracy denominator: 781 per condition. ASR denominators are shown explicitly.',
            'Clean and filtered-clean rows describe baseline accuracy; their changes are not attack success.', '',
            '| Model | Filter | Epsilon | Pipeline | Accuracy (%) | ASR (%) | Successes / denominator |',
            '|---|---|---:|---|---:|---:|---:|',
        ]
        for condition in report['conditions']:
            for pipeline, metric in condition['metrics'].items():
                attack = pipeline in ('attacked', 'transfer_defended', 'adaptive_defended')
                rate = f"{100 * metric['asr']:.2f}" if attack and metric['asr'] is not None else 'N/A'
                counts = f"{metric['asr_successes']} / {metric['asr_denominator']}" if attack else 'N/A'
                lines.append(f"| {condition['model']} | {condition['method']} | {condition['epsilon']:g} | {pipeline} | {100 * metric['accuracy']:.2f} | {rate} | {counts} |")
        (stage / 'SUMMARY.md').write_text('\n'.join(lines) + '\n')
        index = {
            'captured_at': datetime.now(timezone.utc).isoformat(),
            'live_status': False,
            'independent_verification_approval': False,
            'source_commit': report['source_commit'],
            'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(stage.iterdir())},
        }
        (stage / 'snapshot.json').write_text(json.dumps(index, indent=2) + '\n')
        # No published destination is created until all hashes/metrics have passed.
        if destination.exists():
            raise FileExistsError(destination)
        stage.rename(destination)
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(capture(args.source, args.destination, args.repo_root), indent=2))


if __name__ == '__main__':
    main()
