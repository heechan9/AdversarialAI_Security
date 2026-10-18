"""Append-free progress records for FGSM runs, without changing attack numerics.

A journal records durable whole conditions. It is not proof a process is alive,
independent approval, or permission to mix outputs from different environments.
"""
from __future__ import annotations

import json
import math
import numbers
import os
from pathlib import Path
import re
import tempfile


def validate_request(model, epsilons, sample_limit):
    if not isinstance(model, str) or not re.fullmatch(r'[a-z][a-z0-9_]*', model):
        raise ValueError('model name must be a safe lowercase identifier')
    values = list(epsilons)
    if not values or any(isinstance(v, bool) or not isinstance(v, numbers.Real)
                         or not math.isfinite(v) or not 0 <= v <= 1 for v in values):
        raise ValueError('epsilons must be finite numbers in [0, 1]')
    values = [0.0 if v == 0 else float(v) for v in values]
    # The filenames use :g (six significant digits). Distinct floats can collide.
    if len({f'{v:g}' for v in values}) != len(values):
        raise ValueError('epsilons must have unique output filename tokens')
    if type(sample_limit) is not int or sample_limit < 0:
        raise ValueError('sample_limit must be a nonnegative integer')
    return [float(v) for v in values]


def prepare_output(output, model, initial_record=None):
    """Reserve a model's namespace, preserving other model outputs in the folder."""
    output = Path(output).absolute()
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError('output path must not contain symlinks')
    samples = output / 'samples'
    if samples.is_symlink():
        raise ValueError('sample output directory must not be a symlink')
    occupied = list(output.glob(f'fgsm_{model}*')) + list(samples.glob(f'{model}_eps_*'))
    if occupied:
        raise FileExistsError('FGSM outputs already exist for this model; use a new output directory')
    output.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also prevents concurrent evaluators claiming this model.
    journal = output / f'fgsm_{model}_execution.json'
    with journal.open('x', encoding='utf-8') as stream:
        json.dump(initial_record if initial_record is not None else
                  {'schema_version': 1, 'model': model, 'status': 'PREPARING'}, stream, allow_nan=False)
    return journal


def write_progress(path, record):
    """Replace only this run's journal atomically; never touch research CSVs."""
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
