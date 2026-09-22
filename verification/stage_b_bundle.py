"""Read-only integrity check of a transferred Stage B result directory.

Inspired by bunkering-ai scripts/source_changes.py and audit_diagnostic_snapshot.py.
Integrity is not authenticity, successful inference, or independent verification.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError('non-finite JSON value: ' + value)


def audit(directory, expected_report_sha256=None):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('bundle must be a real directory')
    directory = directory.resolve()
    files = {}
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError('symbolic links are not accepted')
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = digest(path)
        elif not path.is_dir():
            raise ValueError('non-regular bundle entry')
    report_hash = files.pop('rerun-report.json', None)
    if report_hash is None:
        raise ValueError('missing rerun-report.json')
    if expected_report_sha256 is not None:
        if not re.fullmatch('[0-9a-f]{64}', expected_report_sha256):
            raise ValueError('expected report hash must be lowercase SHA256')
        if report_hash != expected_report_sha256:
            raise ValueError('report differs from supplied reference hash')
    report = json.loads((directory / 'rerun-report.json').read_text(encoding='utf-8'),
                        object_pairs_hook=unique_pairs, parse_constant=reject_constant)
    if not isinstance(report, dict):
        raise ValueError('report must be an object')
    expected = report.get('artifact_sha256')
    if not isinstance(expected, dict) or not expected:
        raise ValueError('missing or empty artifact manifest')
    for name, value in expected.items():
        p = PurePosixPath(name)
        if (not name or p.is_absolute() or '..' in p.parts or '\\' in name
                or ':' in name or p.as_posix() != name or name == 'rerun-report.json'):
            raise ValueError('unsafe/noncanonical manifest path: ' + name)
        if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
            raise ValueError('invalid artifact SHA256: ' + name)
    added = sorted(files.keys() - expected.keys())
    removed = sorted(expected.keys() - files.keys())
    changed = sorted(k for k in files.keys() & expected.keys() if files[k] != expected[k])
    return {'integrity_status': 'FAIL' if added or removed or changed else 'PASS',
            'recorded_execution_status': report.get('status', 'UNKNOWN'),
            'report_sha256': report_hash,
            'report_hash_reference_checked': expected_report_sha256 is not None,
            'checked_files': len(files), 'added': added, 'removed': removed, 'changed': changed,
            'limitation': 'File integrity only; does not rerun inference, validate metrics, or authenticate the operator.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--expected-report-sha256')
    args = parser.parse_args()
    try:
        result = audit(args.bundle, args.expected_report_sha256)
    except (OSError, ValueError) as exc:
        parser.exit(2, f'Invalid bundle: {exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['integrity_status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
