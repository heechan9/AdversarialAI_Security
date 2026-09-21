"""Read-only canonical CSV/JSON to MARIS comparison; never execute a model."""
import argparse
import json
from pathlib import Path

try:
    from .stage_b_run import read_rows, compare_json
    from .stage_b_readiness import _load_json
except ImportError:
    from stage_b_run import read_rows, compare_json
    from stage_b_readiness import _load_json


def counts(rows):
    clean = sum(r['clean_predicted_label'] == r['true_label'] for r in rows)
    robust = sum(r['adversarial_predicted_label'] == r['true_label'] for r in rows)
    successes = sum(r['clean_predicted_label'] == r['true_label'] and
                    r['adversarial_predicted_label'] != r['true_label'] for r in rows)
    return dict(n=len(rows), cleanCorrect=clean, robustCorrect=robust,
                successes=successes, asr=successes/clean if clean else None)


def check(root):
    root = Path(root)
    web = root/'web/maris/public/evidence'
    data = _load_json(web/'data.json')
    models, epsilons = ['cnn', 'mobilenet'], [0., .01, .03, .05]
    classes = list(_load_json(root/'configs/classes.json').values())
    if data['models'] != models or data['epsilons'] != epsilons or data['classNames'] != classes or data['total'] != 781:
        raise ValueError('MARIS scope differs')
    expected, sources = [], {}
    for model in models:
        for eps in epsilons:
            rows = read_rows(root/f'results/attacks/provisional/fgsm_{model}_eps_{eps:g}_samples.csv')
            if len(rows) != 781 or len({r['relative_path'] for r in rows}) != 781:
                raise ValueError('canonical sample coverage differs')
            sources[model, eps] = rows
            expected.append(dict(model=model, epsilon=eps, **counts(rows), classes=[
                dict(name=name, **counts([r for r in rows if r['true_label']==name])) for name in classes]))
    compare_json(expected, data['results'], 1e-12, 'MARIS FGSM')
    for sample in data['samples']:
        rows = sources[sample['model'], sample['epsilon']]
        row = next(r for r in rows if r['relative_path'].replace('\\','/') == sample['path'])
        cleanfile = 'cnn_baseline' if sample['model']=='cnn' else 'mobilenet'
        clean = next(r for r in read_rows(root/f'results/clean/{cleanfile}_eval.csv')
                     if r['relative_path'].replace('\\','/') == sample['path'])
        expected_sample = dict(truth=row['true_label'], cleanPrediction=row['clean_predicted_label'],
                               attackPrediction=row['adversarial_predicted_label'],
                               success=row['clean_predicted_label']==row['true_label'] and row['adversarial_predicted_label']!=row['true_label'],
                               cleanScore=float(clean[f"prob_{clean['predicted_index']}_{clean['predicted_label']}"]))
        compare_json(expected_sample, {k:sample[k] for k in expected_sample}, 1e-12, 'MARIS sample')
    defense = _load_json(web/'defense-comparison.json')
    if defense['models'] != models or defense['epsilons'] != epsilons or [m['id'] for m in defense['methods']] != ['gaussian','mean']:
        raise ValueError('MARIS defense coverage differs')
    for method in defense['methods']:
        summary = _load_json(root/f"results/defenses/experimental/{method['id']}_run_01/summary.json")
        expected = [{k:r[k] for k in ('model','epsilon','overall')} for r in summary]
        compare_json(expected, method['results'], 1e-12, 'MARIS '+method['id'])
    return dict(status='PASS', fgsm_conditions=8, defense_conditions=16,
                sample_cards=len(data['samples']), model_execution=False)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path('.'))
    print(json.dumps(check(parser.parse_args().repo_root),indent=2))
