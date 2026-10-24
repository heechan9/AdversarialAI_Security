"""Export the public one-seed follow-up from audited saved records; no inference."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
SOURCE = '13d92a15c3b8953e24b5d44326cd2327973a7a25'
RELATIVE = 'results/extensions/matched_cnn_20261024'
DIRECTORY = ROOT / RELATIVE


def main():
    index = json.loads((DIRECTORY / 'evidence-index.json').read_text())
    paths = [f'{RELATIVE}/{name}' for name in index['files']]
    paths += [f'{RELATIVE}/evidence-index.json', 'verification/matched_cnn_saved_audit.py']
    for relative in paths:
        pinned = subprocess.check_output(['git', 'show', f'{SOURCE}:{relative}'], cwd=ROOT)
        if pinned != (ROOT / relative).read_bytes():
            raise ValueError('Published source bytes differ: ' + relative)
    spec = importlib.util.spec_from_file_location('saved_audit', ROOT / 'verification/matched_cnn_saved_audit.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    audited = module.audit(DIRECTORY)
    evaluation = json.loads((DIRECTORY / 'evaluation.json').read_text())
    report = {
        'schema': 'maris-matched-cnn/v1',
        'sourceCommit': SOURCE,
        'trainingSourceCommit': evaluation['source_commit'],
        'status': evaluation['status'],
        'completedAt': evaluation['updated_at'],
        'samplesPerModel': 781,
        'settings': evaluation['settings'],
        'models': {name: {**values,
                   'modelSha256': evaluation['models'][name]['model_sha256'],
                   'csvSha256': evaluation['models'][name]['csv_sha256']}
                   for name, values in audited['models'].items()},
        'mixedMinusCleanOnly': audited['mixed_minus_clean_only'],
        'plannedTrainingSeeds': [2026, 2027, 2028],
        'completedTrainingSeeds': [2026],
        'unrunTrainingSeeds': [2027, 2028],
        'scope': {'model': 'CNN', 'preprocessing': 'none', 'split': 'historical canonical test',
                  'independentReproductionComplete': False, 'existingExternalStageB': 'FAIL'},
        'pairedAudit': evaluation['paired_audit'],
        'sourceSha256': {relative: hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
                         for relative in paths},
        'savedVerification': audited['status'],
        'independentVerificationApproval': False,
    }
    output = ROOT / 'web/maris/public/evidence/matched-cnn-followup.json'
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print('Exported audited one-seed follow-up; no model inference.')


if __name__ == '__main__':
    main()
