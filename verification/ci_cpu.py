"""CPU regression entry point. No private inputs or canonical output writes."""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET


def require_executed_tests(path):
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    if not cases:
        raise RuntimeError('Required CPU suite collected no tests')
    skipped = [case.attrib.get('name') for case in cases if case.find('skipped') is not None]
    if skipped:
        raise RuntimeError(f'Required CPU tests were skipped: {skipped}')


def require_preserved_inputs(repo_root=Path('.')):
    status = subprocess.check_output(
        ['git', 'status', '--porcelain', '--untracked-files=all', '--',
         'src', 'configs', 'results'], cwd=repo_root, text=True)
    if status:
        raise RuntimeError(f'Protected input files changed or were added:\n{status}')


def main():
    out = Path('ci-artifacts')
    out.mkdir(exist_ok=True)
    env = {
        'python': sys.version, 'platform': platform.platform(),
        'checkout_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'pr_head_sha': os.getenv('PR_HEAD_SHA'),
        'settings': {key: os.getenv(key, 'unset/native-default') for key in
                     ('TF_ENABLE_ONEDNN_OPTS', 'TF_DETERMINISTIC_OPS',
                      'TF_NUM_INTRAOP_THREADS', 'TF_NUM_INTEROP_THREADS', 'CUDA_VISIBLE_DEVICES')},
        'scope': 'CPU synthetic regression and public saved evidence only',
        'separate_validation': ['SurFree torch adapter: blackbox-series.yml',
                                'Private official models and 781-image inference',
                                'Full GPU extensions and independent operator approval'],
    }
    (out / 'environment.json').write_text(json.dumps(env, indent=2), encoding='utf-8')
    with (out / 'pip-freeze.txt').open('w') as f:
        subprocess.run([sys.executable, '-m', 'pip', 'freeze'], stdout=f, check=True)
    # Import failures must fail before pytest.importorskip can hide missing dependencies.
    import tensorflow as tf
    import keras
    import numpy
    import pandas
    import sklearn
    import matplotlib
    import PIL
    import yaml
    assert tf.__version__ == '2.21.0', tf.__version__
    assert keras.__version__ == '3.15.1', keras.__version__
    env.update(tensorflow=tf.__version__, keras=keras.__version__,
               devices=[str(d) for d in tf.config.list_physical_devices()],
               tensorflow_build=tf.sysconfig.get_build_info())
    (out / 'environment.json').write_text(json.dumps(env, indent=2), encoding='utf-8')
    code = subprocess.call([sys.executable, '-m', 'pytest', 'tests', '-q', '-ra',
                            '--ignore=tests/test_surfree_adapter.py',
                            '--junitxml=ci-artifacts/junit.xml'])
    if code:
        return code
    require_executed_tests(out / 'junit.xml')
    from adversarial_ai.audit.runner import run_full_audit
    from adversarial_ai.audit.paper_claims import audit_paper_claims
    run_full_audit(repo_root=Path('.'), output_report_path=out / 'evidence-audit.json')
    claims = audit_paper_claims(Path('.'))
    (out / 'paper-claims.json').write_text(json.dumps([c.to_dict() for c in claims], indent=2), encoding='utf-8')
    require_preserved_inputs()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
