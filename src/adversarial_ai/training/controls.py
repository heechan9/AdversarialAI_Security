"""Recorded protocol matching for clean-only versus mixed-PGD training controls.

Matching metadata is not proof of execution or independent validation. The
original checkpoint's historical data exposure is not removed by either arm.
"""
import hashlib
import json
import math
import re


WEIGHTS = {'pgd_mixed': 0.5, 'clean_only': 1.0}
SETTINGS = ('model', 'epochs', 'epsilon', 'step_size', 'steps', 'seed',
            'batch_size', 'learning_rate')
LOCATION_SETTINGS = ('run_id', 'training_mode', 'train_dir', 'validation_dir', 'test_dir')


def protocol_hash(protocol):
    return hashlib.sha256(json.dumps(protocol, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def control_metadata(record):
    """Bind the shared protocol to content identity, excluding mode and run paths."""
    settings = record['settings']
    if set(settings) != set(SETTINGS + LOCATION_SETTINGS):
        raise ValueError('unknown or missing training settings; protocol schema requires review')
    mode = settings['training_mode']
    if mode not in WEIGHTS:
        raise ValueError('invalid training control mode')
    if not isinstance(settings['run_id'],str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,79}',settings['run_id']):
        raise ValueError('invalid training run ID')
    for key in ('train_dir','validation_dir','test_dir'):
        if not isinstance(settings[key],str) or not settings[key]:
            raise ValueError('invalid input path setting: ' + key)
    for key in ('tensorflow','keras'):
        if not isinstance(record[key],str) or not record[key]:
            raise ValueError('invalid framework version: ' + key)
    for key, length in (('source_commit', 40), ('source_model_sha256', 64),
                        ('split_audit_sha256', 64)):
        if not isinstance(record[key], str) or not re.fullmatch('[0-9a-f]{%d}' % length, record[key]):
            raise ValueError('invalid training control identity: ' + key)
    if settings['model'] not in ('cnn', 'mobilenet'):
        raise ValueError('invalid model kind')
    for key in ('epochs', 'steps', 'batch_size', 'seed'):
        minimum = 0 if key == 'seed' else 1
        if type(settings[key]) is not int or settings[key] < minimum:
            raise ValueError('invalid integer training setting: ' + key)
    if settings['seed'] >= 2**31:
        raise ValueError('invalid seed')
    for key in ('epsilon', 'step_size', 'learning_rate'):
        value = settings[key]
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('invalid numeric training setting: ' + key)
    if not 0 <= settings['epsilon'] <= 1 or not 0 < settings['step_size'] <= 1 or settings['learning_rate'] <= 0:
        raise ValueError('out-of-range training setting')
    runtime = record['runtime']
    if not isinstance(runtime, dict) or set(runtime) != {'python', 'numpy', 'platform', 'numerical_environment'}:
        raise ValueError('incomplete runtime identity')
    if any(not isinstance(runtime[key], str) or not runtime[key] for key in ('python', 'numpy', 'platform')):
        raise ValueError('invalid runtime version')
    env = runtime['numerical_environment']
    if not isinstance(env, dict) or set(env) != {'TF_ENABLE_ONEDNN_OPTS', 'TF_DETERMINISTIC_OPS',
            'TF_NUM_INTRAOP_THREADS', 'TF_NUM_INTEROP_THREADS', 'OMP_NUM_THREADS', 'CUDA_VISIBLE_DEVICES'}:
        raise ValueError('incomplete numerical environment')
    if any(v is not None and not isinstance(v, str) for v in env.values()):
        raise ValueError('invalid numerical environment')
    protocol = {
        'schema_version': 1,
        'source_commit': record['source_commit'],
        'source_model_sha256': record['source_model_sha256'],
        'split_audit_sha256': record['split_audit_sha256'],
        'settings': {key: settings[key] for key in SETTINGS},
        'tensorflow': record['tensorflow'], 'keras': record['keras'],
        'runtime': runtime,
        'optimizer': 'Adam',
        'training_order': 'default_rng(seed + epoch).permutation(train.n)',
        'selection': 'highest validation PGD accuracy; earliest epoch wins ties',
        'validation_attack': 'PGD; training epsilon/step_size/steps; one restart; seed + batch',
        'comparison': 'same initialization/data/configuration; clean_only versus 50:50 clean/PGD loss',
    }
    return dict(training_mode=mode, clean_weight=WEIGHTS[mode],
                comparison_protocol=protocol,
                comparison_protocol_sha256=protocol_hash(protocol))


def compare_controls(first, second):
    """Validate completed reports and return their common recorded protocol.

    Caller verifies the associated split-audit and selected checkpoint bytes.
    Different modes deliberately have different resume identities, even though
    their shared comparison protocol hashes match.
    """
    reports = [first, second]
    if {r.get('training_mode') for r in reports} != set(WEIGHTS):
        raise ValueError('one clean_only and one pgd_mixed report required')
    protocols = []
    for report in reports:
        if (report.get('kind') != 'adversarial_training_followup' or
                report.get('status') != 'TRAINED_NOT_TEST_EVALUATED'):
            raise ValueError('completed training reports required; not test evaluation')
        expected = control_metadata(report)
        if (type(report.get('clean_weight')) is not float or
                any(report.get(key) != value for key, value in expected.items())):
            raise ValueError('training control metadata mismatch')
        epochs = report['epochs']
        if (any(type(e['epoch']) is not int for e in epochs) or
                [e['epoch'] for e in epochs] != list(range(1, report['settings']['epochs'] + 1))):
            raise ValueError('incomplete training epoch coverage')
        scores = [e['validation_pgd_accuracy'] for e in epochs]
        if not scores or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in scores):
            raise ValueError('invalid validation scores')
        if type(report.get('best_epoch')) is not int or report.get('best_epoch') != scores.index(max(scores)) + 1:
            raise ValueError('validation selection mismatch')
        if not isinstance(report.get('trained_model_sha256'), str) or not re.fullmatch('[0-9a-f]{64}', report['trained_model_sha256']):
            raise ValueError('selected checkpoint identity missing')
        protocols.append(expected['comparison_protocol'])
    if protocols[0] != protocols[1]:
        raise ValueError('paired training protocols differ')
    return protocols[0]
