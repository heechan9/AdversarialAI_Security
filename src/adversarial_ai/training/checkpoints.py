"""Immutable, hash-checked epoch snapshots; incomplete copies are not resumable."""
import hashlib
import json
from pathlib import Path
import shutil
import uuid


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save_snapshot(root, model, best_model, state):
    """Publish state last and atomically rename a complete epoch snapshot."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    name = f"epoch-{state['next_epoch']:04d}-{uuid.uuid4().hex}"
    temp = root / ('.pending-' + name)
    temp.mkdir()
    try:
        model.save(temp / 'last.keras')  # compiled optimizer state is included
        shutil.copy2(best_model, temp / 'best.keras')
        record = dict(state, files={n: digest(temp / n) for n in ('last.keras', 'best.keras')})
        (temp / 'state.json').write_text(json.dumps(record, indent=2, allow_nan=False) + '\n')
        temp.rename(root / name)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return root / name


def latest_snapshot(root, identity):
    valid = []
    for path in Path(root).glob('epoch-*'):
        try:
            if path.is_symlink() or not path.is_dir() or (path / 'state.json').is_symlink():
                continue
            state = json.loads((path / 'state.json').read_text())
            if state['identity'] != identity:
                continue
            if set(state['files']) != {'last.keras', 'best.keras'}:
                continue
            if any((path / n).is_symlink() or digest(path / n) != h for n, h in state['files'].items()):
                continue
            if state['next_epoch'] != len(state['report']['epochs']) or state['next_epoch'] < 1:
                continue
            valid.append((state['next_epoch'], path.name, path, state))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    if not valid:
        raise ValueError('No complete checkpoint matching source, data and settings; use a new run ID.')
    _, _, path, state = max(valid)
    return path, state
