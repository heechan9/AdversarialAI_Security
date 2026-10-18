"""Saved-output and interrupted-invocation checks; no private inference or result edits."""
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

from adversarial_ai.evaluation import fgsm_evaluation as evaluation
from adversarial_ai.evaluation.clean_baseline import EvaluationSpec
from adversarial_ai.evaluation.fgsm_progress import prepare_output, validate_request, write_progress
from verification.fgsm_run_audit import audit, read_json

ROOT = Path(__file__).resolve().parents[1]
SAVED = ROOT/'results/attacks/provisional'


def copy_conditions(tmp_path, epsilons=(0., .01, .03), model='mobilenet'):
    out = tmp_path/'partial'
    out.mkdir()
    for epsilon in epsilons:
        name = f'fgsm_{model}_eps_{epsilon:g}_samples.csv'
        shutil.copyfile(SAVED/name, out/name)
    return out


def mutate_csv(path, mutate):
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    mutate(rows)
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def test_public_saved_coverage_is_not_an_execution_approval():
    result = audit([SAVED], ROOT)
    assert result['checked_conditions'] == 8
    assert result['result'] == 'FULL_REQUESTED_SAVED_SAMPLE_COVERAGE'
    assert result['independent_verification_approval'] is False
    assert result['probabilities_compared'] is False
    assert result['process_liveness'] == 'NOT_CHECKED'
    assert all(not v['completion_record_consistent'] for v in result['invocations'])


def test_legacy_interruption_plans_only_missing_epsilon_without_writes(tmp_path):
    out = copy_conditions(tmp_path)
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    result = audit([out], ROOT, ['mobilenet'])
    assert result['result'] == 'PARTIAL_SAVED_SAMPLE_COVERAGE'
    assert result['checked_conditions'] == 3
    assert result['missing_conditions'] == [{'model':'mobilenet', 'epsilon':.05}]
    assert result['resume_plan'] == [{'model':'mobilenet', 'epsilons':[.05],
                                    'output_requirement':'NEW_DIRECTORY_OUTSIDE_ALL_PRIOR_OUTPUTS'}]
    assert result['invocations'][0]['provenance'] == 'LEGACY_EXECUTION_PROVENANCE_UNVERIFIED'
    assert {p.name:p.read_bytes() for p in out.iterdir()} == before


@pytest.mark.parametrize('mutation, message', [
    (lambda r:r.pop(), 'incomplete sample'),
    (lambda r:r.__setitem__(1, r[0].copy()), 'order/path'),
    (lambda r:r[0].update(epsilon='nan'), 'epsilon mismatch'),
    (lambda r:r[0].update(true_index='10'), 'class index'),
    (lambda r:r[0].update(clean_predicted_label='bad'), 'class label'),
    (lambda r:r[0].update(clean_correct='true'), 'clean-correct flag'),
    (lambda r:r[0].update(attack_success='True' if r[0]['attack_success']=='False' else 'False'), 'attack-success flag'),
    (lambda r:r[0].update(linf='nan'), 'perturbation'),
    (lambda r:r[0].update(linf='inf'), 'perturbation'),
    (lambda r:r[0].update(linf='-.01'), 'perturbation'),
    (lambda r:r[0].update(linf='.02'), 'perturbation'),
])
def test_corrupted_partial_condition_never_enters_resume_plan(tmp_path, mutation, message):
    out = copy_conditions(tmp_path, (.01,))
    mutate_csv(out/'fgsm_mobilenet_eps_0.01_samples.csv', mutation)
    with pytest.raises(ValueError, match=message):
        audit([out], ROOT, ['mobilenet'])


def test_zero_epsilon_requires_exact_zero_linf(tmp_path):
    out = copy_conditions(tmp_path, (0.,))
    mutate_csv(out/'fgsm_mobilenet_eps_0_samples.csv', lambda r:r[0].update(linf='0.0000001'))
    with pytest.raises(ValueError, match='epsilon-zero'):
        audit([out], ROOT, ['mobilenet'])


def test_partial_cli_exits_nonzero_unless_explicitly_planning(tmp_path):
    out = copy_conditions(tmp_path)
    command = [sys.executable, str(ROOT/'verification/fgsm_run_audit.py'), str(out), '--models', 'mobilenet']
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 2
    assert json.loads(result.stdout)['checked_conditions'] == 3
    result = subprocess.run(command+['--allow-partial'], capture_output=True, text=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)['result'] == 'PARTIAL_SAVED_SAMPLE_COVERAGE'


def test_duplicate_sources_are_ambiguous_even_if_bytes_match(tmp_path):
    out = copy_conditions(tmp_path)
    other = tmp_path/'other'; shutil.copytree(out, other)
    with pytest.raises(ValueError, match='ambiguous duplicate'):
        audit([out, other], ROOT, ['mobilenet'])


def test_multi_directory_coverage_retains_separate_provenance(tmp_path):
    out = copy_conditions(tmp_path)
    other = tmp_path/'resume'; other.mkdir()
    shutil.copyfile(SAVED/'fgsm_mobilenet_eps_0.05_samples.csv', other/'fgsm_mobilenet_eps_0.05_samples.csv')
    result = audit([out,other], ROOT, ['mobilenet'])
    assert result['result'] == 'FULL_REQUESTED_SAVED_SAMPLE_COVERAGE'
    assert len(result['invocations']) == 2
    assert not any(v['completion_record_consistent'] for v in result['invocations'])


@pytest.mark.parametrize('epsilon', [float('nan'), float('inf'), -float('inf'), True, False, np.bool_(True), -.1, 1.1, '0.1'])
def test_invalid_epsilon_rejected_before_output_created(tmp_path, epsilon):
    with pytest.raises(ValueError, match='epsilons'):
        evaluation.evaluate_fgsm(EvaluationSpec('cnn', Path('absent'), (128,128)), Path('absent'),
                                 Path('absent'), tmp_path/'new', [epsilon])
    assert not (tmp_path/'new').exists()


def test_filename_rounding_collision_rejected():
    with pytest.raises(ValueError, match='filename'):
        validate_request('cnn', [.01, .010000000000000002], 2)


@pytest.mark.parametrize('sample_limit', [-1, True, .5])
def test_invalid_sample_limit_rejected(sample_limit):
    with pytest.raises(ValueError, match='sample_limit'):
        validate_request('cnn', [.01], sample_limit)


def test_existing_outputs_are_preserved_before_model_loading(tmp_path, monkeypatch):
    out = copy_conditions(tmp_path)
    before = {p.name:p.read_bytes() for p in out.iterdir()}
    monkeypatch.setattr(evaluation, '_evaluate_fgsm', lambda *a:pytest.fail('must fail before model loading'))
    with pytest.raises(FileExistsError, match='new output directory'):
        evaluation.evaluate_fgsm(EvaluationSpec('mobilenet',Path('absent'),(224,224)),Path('absent'),
                                 Path('absent'),out,[.05])
    assert {p.name:p.read_bytes() for p in out.iterdir()} == before


def test_other_model_output_can_share_directory(tmp_path):
    (tmp_path/'fgsm_cnn.csv').write_text('do not change')
    journal = prepare_output(tmp_path, 'mobilenet')
    assert journal.exists()
    assert (tmp_path/'fgsm_cnn.csv').read_text() == 'do not change'
    with pytest.raises(FileExistsError):
        prepare_output(tmp_path, 'mobilenet')


def test_symlinks_are_rejected(tmp_path):
    out = copy_conditions(tmp_path)
    link = tmp_path/'link'; link.symlink_to(out, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        prepare_output(link, 'cnn')
    with pytest.raises(ValueError, match='symlink'):
        audit([link],ROOT,['mobilenet'])


def test_atomic_progress_failure_keeps_previous_journal(tmp_path):
    journal = prepare_output(tmp_path, 'cnn')
    before = journal.read_bytes()
    with pytest.raises(ValueError):
        write_progress(journal, {'bad':float('nan')})
    assert journal.read_bytes() == before
    assert not list(tmp_path.glob('*.tmp'))


@pytest.mark.parametrize('exception,status', [(KeyboardInterrupt(),'INTERRUPTED'), (RuntimeError('boom'),'ERROR')])
def test_interruption_records_exact_completed_conditions(tmp_path, monkeypatch, exception, status):
    def interrupted(*args):
        progress, journal = args[-2:]
        progress['conditions'].append({'epsilon':0.,'samples':781})
        write_progress(journal, progress)
        raise exception
    monkeypatch.setattr(evaluation, '_evaluate_fgsm', interrupted)
    with pytest.raises(type(exception)):
        evaluation.evaluate_fgsm(EvaluationSpec('cnn',Path('absent'),(128,128)),Path('absent'),
                                 Path('absent'),tmp_path,[0.,.01])
    record = read_json(tmp_path/'fgsm_cnn_execution.json')
    assert record['status'] == status
    assert record['conditions'] == [{'epsilon':0.,'samples':781}]
    assert record['independent_verification_approval'] is False
    assert 'finished_utc' in record


def test_invalid_preparing_record_cannot_claim_completion(tmp_path):
    out = copy_conditions(tmp_path)
    (out/'fgsm_mobilenet_execution.json').write_text(json.dumps({
        'schema_version':1,'kind':'fgsm_evaluation_progress','model':'mobilenet',
        'independent_verification_approval':False,'status':'COMPLETED_REQUESTED_SCOPE',
        'epsilons':[0.,.01,.03,.05], 'conditions':[], 'model_sha256':'fake'}))
    with pytest.raises(ValueError, match='identity'):
        audit([out],ROOT,['mobilenet'])


@pytest.fixture
def synthetic_runtime(monkeypatch):
    """Exercise real TensorFlow FGSM on generated pixels with a synthetic model.

    Directory loading and private input hashing are mocked; no scientific result
    or private-model reproduction is represented by these integration tests.
    """
    import tensorflow as tf
    manifest = read_json(ROOT/'configs/test_manifest.json')
    classes = read_json(ROOT/'configs/classes.json')
    labels = {value:int(key) for key,value in classes.items()}
    class Generator:
        class_indices = labels
        filenames = [v['relative_path'] for v in manifest['test_files']]
        samples = 781
        batch_size = 32
        def __len__(self):
            return 25
        def __getitem__(self, index):
            selected = manifest['test_files'][index*32:(index+1)*32]
            x = np.full((len(selected),2,2,1),.5,np.float32)
            y = np.eye(10,dtype=np.float32)[[labels[v['label']] for v in selected]]
            return x,y
    class DataGenerator:
        def __init__(self, **kwargs):
            assert kwargs == {'rescale':1./255.}
        def flow_from_directory(self, *args, **kwargs):
            assert kwargs['shuffle'] is False
            return Generator()
    inputs = tf.keras.Input((2,2,1))
    outputs = tf.keras.layers.Dense(10,activation='softmax',
        kernel_initializer=tf.keras.initializers.Constant(np.tile(np.linspace(.8,-.8,10),(4,1))),
        bias_initializer='zeros')(tf.keras.layers.Flatten()(inputs))
    model = tf.keras.Model(inputs,outputs)
    monkeypatch.setattr(tf.keras.preprocessing.image,'ImageDataGenerator',DataGenerator)
    monkeypatch.setattr(tf.keras.models,'load_model',lambda *a,**k:model)
    model_hash = next(v['sha256'] for v in manifest['models'] if v['path']=='models/cnn_baseline.h5')
    calls = []
    def validate(**kwargs):
        calls.append(kwargs)
        return model_hash
    monkeypatch.setattr(evaluation,'validate_reproducibility_manifest',validate)
    return model,calls


def execute_synthetic(out, epsilons):
    evaluation.evaluate_fgsm(EvaluationSpec('cnn',Path('models/cnn_baseline.h5'),(128,128)),
        Path('synthetic-only'),ROOT/'configs/classes.json',out,epsilons,
        sample_limit=0,manifest_path=ROOT/'configs/test_manifest.json')


def test_real_tf_condition_journal_survives_interruption(tmp_path,monkeypatch,synthetic_runtime):
    original = evaluation._run_epsilon
    def interrupted(*args):
        if args[2] == .01:
            raise KeyboardInterrupt()
        return original(*args)
    monkeypatch.setattr(evaluation,'_run_epsilon',interrupted)
    with pytest.raises(KeyboardInterrupt):
        execute_synthetic(tmp_path,[0.,.01])
    journal = read_json(tmp_path/'fgsm_cnn_execution.json')
    assert journal['status'] == 'INTERRUPTED'
    assert len(journal['conditions']) == 1
    assert journal['conditions'][0]['epsilon'] == 0.
    assert not (tmp_path/'fgsm_cnn_metadata.json').exists()
    result = audit([tmp_path],ROOT,['cnn'],[0.,.01])
    assert result['checked_conditions'] == 1
    assert result['missing_conditions'] == [{'model':'cnn','epsilon':.01}]
    assert result['invocations'][0]['journal_status'] == 'INTERRUPTED'
    assert not result['invocations'][0]['completion_record_consistent']


def test_real_tf_completed_subset_does_not_claim_full_grid(tmp_path,synthetic_runtime):
    model,calls = synthetic_runtime
    before = [weight.numpy().copy() for weight in model.weights]
    execute_synthetic(tmp_path,[.05])
    assert len(calls) == 2  # Input integrity is rechecked before completion.
    result = audit([tmp_path],ROOT,['cnn'])
    assert result['checked_conditions'] == 1
    assert result['result'] == 'PARTIAL_SAVED_SAMPLE_COVERAGE'
    assert result['invocations'][0]['completion_record_consistent'] is True
    assert result['resume_plan'][0]['epsilons'] == [0.,.01,.03]
    for left,right in zip(before,model.weights):
        np.testing.assert_array_equal(left,right.numpy())
    journal = read_json(tmp_path/'fgsm_cnn_execution.json')
    journal['status'] = 'RUNNING'  # Hard termination can leave this stale.
    write_progress(tmp_path/'fgsm_cnn_execution.json',journal)
    result = audit([tmp_path],ROOT,['cnn'],[.05])
    assert result['result'] == 'FULL_REQUESTED_SAVED_SAMPLE_COVERAGE'
    assert not result['invocations'][0]['completion_record_consistent']
    assert result['process_liveness'] == 'NOT_CHECKED'


def test_completed_journal_hash_tampering_fails(tmp_path,synthetic_runtime):
    execute_synthetic(tmp_path,[0.])
    path = tmp_path/'fgsm_cnn_eps_0_confusion_matrix.png'
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='artifact hash mismatch'):
        audit([tmp_path],ROOT,['cnn'],[0.])


def test_negative_zero_is_normalized_and_duplicate_zero_rejected():
    assert validate_request('cnn', [-0.0], 2) == [0.0]
    assert str(validate_request('cnn', [-0.0], 2)[0]) == '0.0'
    with pytest.raises(ValueError, match='filename'):
        validate_request('cnn', [-0.0, 0.0], 2)


def test_relative_output_does_not_hash_its_own_journal(tmp_path,monkeypatch,synthetic_runtime):
    monkeypatch.chdir(tmp_path)
    execute_synthetic(Path('relative-output'),[0.])
    journal = read_json(tmp_path/'relative-output/fgsm_cnn_execution.json')
    assert 'fgsm_cnn_execution.json' not in journal['artifact_sha256']
    result = audit([Path('relative-output')],ROOT,['cnn'],[0.])
    assert result['invocations'][0]['completion_record_consistent'] is True


def test_full_initial_journal_exists_before_first_progress_replace(tmp_path,monkeypatch):
    original = evaluation.write_progress
    observed = []
    def interrupted(path,record):
        if not observed:
            initial = read_json(path)
            assert initial['kind'] == 'fgsm_evaluation_progress'
            assert initial['epsilons'] == [.05] and initial['conditions'] == []
            assert initial['status'] == 'PREPARING' and initial['run_id']
            observed.append(initial)
            raise KeyboardInterrupt()
        original(path,record)
    monkeypatch.setattr(evaluation,'write_progress',interrupted)
    with pytest.raises(KeyboardInterrupt):
        execute_synthetic(tmp_path,[.05])
    result = audit([tmp_path],ROOT,['cnn'])
    assert result['checked_conditions'] == 0
    assert result['invocations'][0]['provenance'] == 'JOURNAL_WITHOUT_COMPLETED_CONDITIONS'


def corrupt_clean_prediction(rows):
    row = next(v for v in rows if v['clean_correct']=='False')
    new = next(i for i in range(10) if i not in (int(row['true_index']),int(row['clean_predicted_index'])))
    classes = read_json(ROOT/'configs/classes.json')
    row['clean_predicted_index'] = str(new)
    row['clean_predicted_label'] = classes[str(new)]


@pytest.mark.parametrize('use_journal',[False,True])
def test_subset_audit_checks_declared_cross_condition_clean_predictions(tmp_path,use_journal):
    from verification.fgsm_run_audit import audit_condition, sha
    out = copy_conditions(tmp_path,(.01,.03))
    mutate_csv(out/'fgsm_mobilenet_eps_0.03_samples.csv',corrupt_clean_prediction)
    manifest = read_json(ROOT/'configs/test_manifest.json')
    classes = read_json(ROOT/'configs/classes.json')
    summaries = [audit_condition(out/f'fgsm_mobilenet_eps_{e:g}_samples.csv',e,manifest,classes)[0]
                 for e in (.01,.03)]
    if use_journal:
        conditions = []
        for summary in summaries:
            e = summary['epsilon']
            names = [f'fgsm_mobilenet_eps_{e:g}_{suffix}' for suffix in
                     ('samples.csv','report.json','confusion_matrix.csv','confusion_matrix.png')]
            for name in names[1:]:
                shutil.copyfile(SAVED/name,out/name)
            conditions.append(dict(epsilon=e,samples=781,summary=summary,
                                   artifact_sha256={name:sha(out/name) for name in names}))
        journal = dict(schema_version=1,kind='fgsm_evaluation_progress',model='mobilenet',
            independent_verification_approval=False,status='INTERRUPTED',epsilons=[.01,.03],conditions=conditions,
            run_id='synthetic-test',model_sha256=next(v['sha256'] for v in manifest['models'] if 'mobilenet' in v['path']),
            manifest_sha256=sha(ROOT/'configs/test_manifest.json'),classes_sha256=sha(ROOT/'configs/classes.json'))
        (out/'fgsm_mobilenet_execution.json').write_text(json.dumps(journal))
    else:
        with (out/'fgsm_mobilenet.csv').open('w',newline='') as stream:
            writer = csv.DictWriter(stream,fieldnames=list(summaries[0]))
            writer.writeheader(); writer.writerows(summaries)
    with pytest.raises(ValueError,match='clean predictions differ between conditions'):
        audit([out],ROOT,['mobilenet'],[.01])
