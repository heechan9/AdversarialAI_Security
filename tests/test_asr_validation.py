"""Aggregate ASR contracts and exact compatibility with saved valid cells."""
import csv
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from adversarial_ai.evaluation.fgsm_evaluation import compute_untargeted_asr


@pytest.mark.parametrize('bad', [np.array([[0], [1]]), np.array([0]), np.array(0)])
@pytest.mark.parametrize('index', [0, 1, 2])
def test_shape_mismatch_cannot_broadcast(bad, index):
    values = [np.array([0, 1]), np.array([0, 1]), np.array([1, 0])]
    values[index] = bad
    with pytest.raises(ValueError, match='identical shapes'):
        compute_untargeted_asr(*values)


@pytest.mark.parametrize('bad', [np.array([], dtype=int), np.array([[0, 1]]), np.array(0)])
def test_matching_but_invalid_dimensions(bad):
    with pytest.raises(ValueError, match='nonempty one-dimensional'):
        compute_untargeted_asr(bad, bad, bad)


@pytest.mark.parametrize('bad', [np.array([0., 1.]), np.array([True, False]),
    np.array(['0', '1']), np.array([0, 1], dtype=object), np.array([-1, 1]),
    np.array([np.nan, 1.]), np.array([np.inf, 1.])])
@pytest.mark.parametrize('index', [0, 1, 2])
def test_invalid_label_types_or_negative_classes(bad, index):
    values = [np.array([0, 1]), np.array([0, 1]), np.array([1, 0])]
    values[index] = bad
    with pytest.raises(ValueError, match='nonnegative integer'):
        compute_untargeted_asr(*values)


def test_zero_clean_correct_is_undefined_not_zero():
    with pytest.raises(ValueError, match='undefined: no clean-correct samples'):
        compute_untargeted_asr(np.array([0, 1]), np.array([1, 0]), np.array([1, 0]))


@pytest.mark.parametrize('factory', [list, tuple, np.asarray,
    lambda x: np.asarray(x, dtype=np.uint64), lambda x: np.asarray(x, dtype=np.int8)])
def test_valid_sequences_and_integer_dtypes(factory):
    result = compute_untargeted_asr(factory([0, 0, 1, 1]), factory([0, 1, 1, 0]),
                                    factory([1, 0, 1, 1]))
    assert result == (.5, 1, 2)
    assert tuple(type(value) for value in result) == (float, int, int)


def test_measured_zero_remains_valid():
    assert compute_untargeted_asr([0, 1], [0, 1], [0, 1]) == (0., 0, 2)


@pytest.mark.parametrize('model', ['cnn', 'mobilenet'])
@pytest.mark.parametrize('epsilon', [0., .01, .03, .05])
def test_saved_valid_cells_remain_exact(model, epsilon):
    root = Path(__file__).resolve().parents[1] / 'results/attacks/provisional'
    with (root / f'fgsm_{model}_eps_{epsilon:g}_samples.csv').open(newline='') as f:
        rows = list(csv.DictReader(f))
    labels = [np.array([int(row[field]) for row in rows]) for field in
              ['true_index', 'clean_predicted_index', 'adversarial_predicted_index']]
    actual = compute_untargeted_asr(*labels)
    with (root / f'fgsm_{model}.csv').open(newline='') as f:
        summary = next(row for row in csv.DictReader(f)
                       if float(row['epsilon']) == epsilon)
    expected = (float(summary['untargeted_asr']), int(summary['attack_successes']),
                int(summary['asr_denominator_clean_correct']))
    assert actual == expected


def test_runner_reports_condition_and_emits_no_false_summary(tmp_path, monkeypatch):
    tf = pytest.importorskip('tensorflow')
    from adversarial_ai.evaluation import fgsm_evaluation as ev

    model = tf.keras.Sequential([tf.keras.Input((1, 1, 1)), tf.keras.layers.Flatten(),
                                 tf.keras.layers.Dense(2, activation='softmax')])
    generator = SimpleNamespace(samples=781, class_indices={'A': 0, 'B': 1}, filenames=[])
    monkeypatch.setattr(ev, 'load_expected_classes', lambda path: ['A', 'B'])
    monkeypatch.setattr(tf.keras.preprocessing.image.ImageDataGenerator, 'flow_from_directory',
                        lambda *args, **kwargs: generator)
    monkeypatch.setattr(ev, 'validate_reproducibility_manifest', lambda **kwargs: 'a' * 64)
    monkeypatch.setattr(tf.keras.models, 'load_model', lambda path: model)
    # Only this synthetic orchestration fixture supplies two rows. Production
    # manifest/sample count checks remain enabled and unchanged.
    monkeypatch.setattr(ev, '_run_epsilon', lambda *args: dict(
        y_true=np.array([0, 1]), clean_probabilities=np.array([[0., 1.], [1., 0.]]),
        adversarial_probabilities=np.array([[0., 1.], [1., 0.]]), linf=np.zeros(2)))
    out = tmp_path / 'output'
    with pytest.raises(ValueError, match='Cannot summarize cnn FGSM epsilon=0.03: ASR is undefined'):
        ev.evaluate_fgsm(ev.EvaluationSpec('cnn', tmp_path / 'model.h5', (1, 1)),
                         tmp_path / 'data', tmp_path / 'classes.json', out, [.03])
    assert not list(out.glob('fgsm_*'))


@pytest.mark.parametrize('factory', [list, tuple])
@pytest.mark.parametrize('boolean', [True, np.bool_(True)])
@pytest.mark.parametrize('index', [0, 1, 2])
def test_mixed_boolean_integer_sequences_do_not_coerce_silently(factory, boolean, index):
    values = [np.array([0, 1]), np.array([0, 1]), np.array([1, 0])]
    values[index] = factory([0, boolean])
    with pytest.raises(ValueError, match='not booleans'):
        compute_untargeted_asr(*values)


@pytest.mark.parametrize('mask', [[True, False], [False, False], np.ma.nomask])
@pytest.mark.parametrize('index', [0, 1, 2])
def test_masked_arrays_rejected_before_mask_is_discarded(mask, index):
    values = [np.array([0, 1]), np.array([0, 1]), np.array([1, 0])]
    values[index] = np.ma.array(values[index], mask=mask)
    with pytest.raises(ValueError, match='does not accept masked arrays'):
        compute_untargeted_asr(*values)
