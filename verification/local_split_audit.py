"""Read-only exact-duplicate audit of available image splits (not a training gate)."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from PIL import Image


def audit_splits(splits):
    rows = {}
    errors = []
    for split, directory in splits.items():
        directory = Path(directory)
        if not directory.is_dir():
            raise ValueError(f'missing split directory: {split}')
        rows[split] = []
        for path in sorted(directory.rglob('*')):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {'.jpeg', '.jpg', '.png', '.bmp', '.gif'}:
                continue
            relative = path.relative_to(directory).as_posix()
            try:
                raw = path.read_bytes()
                with Image.open(path) as image:
                    rgb = image.convert('RGB')
                    # Include shape: different dimensions can share the same byte stream.
                    pixels = f'{rgb.width}x{rgb.height}:RGB:'.encode() + rgb.tobytes()
                rows[split].append({'path': relative, 'sha256': hashlib.sha256(raw).hexdigest(),
                                    'pixel_sha256': hashlib.sha256(pixels).hexdigest()})
            except (OSError, ValueError) as exc:
                errors.append({'split': split, 'path': relative, 'error_type': type(exc).__name__})
    report = {'scope': 'available files only; completeness must be checked against source inventory',
              'pixel_hash_schema': 'sha256(width + x + height + :RGB: + decoded RGB bytes)',
              'training_ready': False, 'near_duplicate_checked': False, 'decode_errors': errors,
              'splits': {}, 'cross_split_duplicates': {}}
    for split, entries in rows.items():
        duplicate_groups = {}
        for key in ('sha256', 'pixel_sha256'):
            groups = defaultdict(list)
            for row in entries:
                groups[row[key]].append(row['path'])
            duplicate_groups[key] = [group for group in groups.values() if len(group) > 1]
        report['splits'][split] = {'count': len(entries), 'duplicate_groups': duplicate_groups, 'files': entries}
    for key in ('sha256', 'pixel_sha256'):
        groups = defaultdict(list)
        for split, entries in rows.items():
            for row in entries:
                groups[row[key]].append({'split': split, 'path': row['path']})
        report['cross_split_duplicates'][key] = [group for group in groups.values()
                                                if len({row['split'] for row in group}) > 1]
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', type=Path, required=True)
    parser.add_argument('--valid', type=Path, required=True)
    parser.add_argument('--test', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit_splits({key: getattr(args, key) for key in ('train', 'valid', 'test')})
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps({'counts': {k: v['count'] for k, v in report['splits'].items()},
                      'decode_errors': len(report['decode_errors']), 'training_ready': False}))
    if report['decode_errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
