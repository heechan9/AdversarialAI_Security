"""Synthetic source/lineage/no-clobber checks; no model inference."""
import json
from pathlib import Path
import subprocess
import sys


def test_continuation_regression_check():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, str(root / 'verification/continuation_regression_check.py')],
        cwd=root, check=True, text=True, capture_output=True,
    )
    report = json.loads(result.stdout)
    assert report['passed'] == report['total'] == 33
    assert report['synthetic'] is True
    assert report['model_inference'] is False
    assert report['audit_stubbed'] is False
