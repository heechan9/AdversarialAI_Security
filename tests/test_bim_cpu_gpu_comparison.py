"""Guard the documented BIM step-size and CPU-vs-GPU comparison against saved files."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / 'results/extensions'


def test_all_saved_bim_reports_use_the_same_attack_settings():
    reports = sorted(EXT.glob('checkpoints/*/bim/run.json'))
    assert len(reports) == 6
    for path in reports:
        s = json.loads(path.read_text())['settings']
        assert (s['attack'], s['steps'], s['step_size'], s['restarts'], s['seed'], s['batch_size']) == ('bim', 10, 0.005, 1, 0, 32), path


def test_cpu_checkpoint_and_gpu_bim_differences_are_preserved_not_hidden():
    cpu = json.loads((EXT / 'checkpoints/20261002-evening/bim/run.json').read_text())
    gpu = {(r['model'], r['filter'], float(r['epsilon']), r['pipeline']): float(r['accuracy'])
           for r in csv.DictReader((EXT / 'bim_gpu_20261004/metrics.csv').open())}
    compared = differing = 0
    largest = 0
    for c in cpu['conditions']:
        for pipeline, metric in c['metrics'].items():
            key = (c['model'], c['method'], c['epsilon'], pipeline)
            if key not in gpu:
                continue
            compared += 1
            images = round(abs(gpu[key] - metric['accuracy']) * 781)
            if abs(gpu[key] - metric['accuracy']) > 1e-12:
                differing += 1
                largest = max(largest, images)
    assert (compared, differing, largest) == (65, 12, 13)
