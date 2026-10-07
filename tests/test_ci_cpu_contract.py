"""Regressions for silent skips and the real Clean loader contract."""
from pathlib import Path
import numpy as np
import pytest
from verification.ci_cpu import require_executed_tests


@pytest.mark.parametrize('xml', ['<testsuites/>', '<testsuite><testcase name="missing"><skipped/></testcase></testsuite>'])
def test_ci_rejects_empty_or_skipped_suite(tmp_path, xml):
    report = tmp_path / 'junit.xml'
    report.write_text(xml)
    with pytest.raises(RuntimeError, match='no tests|skipped'):
        require_executed_tests(report)


def test_real_clean_loader_rgb_normalization_order_and_size(tmp_path, monkeypatch):
    import tensorflow as tf
    from PIL import Image
    from adversarial_ai.evaluation.clean_baseline import evaluate, EvaluationSpec, load_expected_classes
    classes = load_expected_classes(Path('configs/classes.json'))
    for i, name in enumerate(classes):
        folder = tmp_path / name
        folder.mkdir()
        Image.fromarray(np.full((3, 5, 3), i * 20, np.uint8)).save(folder / 'sample.png')
    original = tf.keras.preprocessing.image.ImageDataGenerator.flow_from_directory
    captured = {}

    def observe(self, *args, **kwargs):
        generator = original(self, *args, **kwargs)
        captured['generator'] = generator
        captured['batch'] = next(generator)
        return generator

    monkeypatch.setattr(tf.keras.preprocessing.image.ImageDataGenerator, 'flow_from_directory', observe)
    with pytest.raises(ValueError, match='Expected 781 test images, found 10'):
        evaluate(EvaluationSpec('synthetic', tmp_path / 'absent.h5', (8, 8)),
                 tmp_path, Path('configs/classes.json'), tmp_path / 'output')
    generator = captured['generator']
    x, y = captured['batch']
    assert generator.shuffle is False
    assert generator.class_indices == {name: i for i, name in enumerate(classes)}
    assert x.shape == (10, 8, 8, 3)
    assert x.dtype == np.float32
    np.testing.assert_allclose(x[:, 0, 0, 0], np.arange(10) * 20 / 255, atol=1e-7)
    np.testing.assert_array_equal(y, np.eye(10))


@pytest.mark.parametrize('kind', ['untracked', 'modified', 'staged', 'ignored'])
def test_ci_rejects_protected_input_changes(tmp_path, kind):
    import subprocess
    from verification.ci_cpu import require_preserved_inputs
    def git(*args):
        subprocess.run(['git', *args], cwd=tmp_path, check=True, capture_output=True)
    git('init')
    (tmp_path / 'results').mkdir()
    tracked = tmp_path / 'results' / 'saved.csv'
    tracked.write_text('original')
    (tmp_path / '.gitignore').write_text('*.pyc\n')
    git('add', '.')
    git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
        'commit', '-m', 'fixture')
    require_preserved_inputs(tmp_path)
    if kind == 'ignored':
        (tmp_path / 'results' / 'zz.pyc').write_bytes(b'unexpected')
    elif kind == 'untracked':
        (tmp_path / 'results' / 'extra.csv').write_text('extra')
    else:
        tracked.write_text('changed')
        if kind == 'staged':
            git('add', '.')
    with pytest.raises(RuntimeError, match='Protected input'):
        require_preserved_inputs(tmp_path)
