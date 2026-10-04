"""Descriptive subset views of saved black-box predictions; no model replay."""
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verification.subset_sensitivity import subsets, sha
from blackbox_series_summary import generate as audit_series


def metric(rows, keep, successful):
    chosen = [r for r in rows if r['relative_path'] in keep]
    assert len(chosen) == len(keep)
    clean = sum(str(r['clean_pred']) == str(r['true_index']) for r in chosen)
    successes = sum(str(r['clean_pred']) == str(r['true_index']) and successful(r) for r in chosen)
    return dict(samples=len(chosen), clean_correct=clean, successes=successes,
                attacked_correct=clean-successes, accuracy=(clean-successes)/len(chosen),
                asr=successes/clean if clean else None)


def generate():
    audit_series()
    subset_path = ROOT/'results/extensions/sensitivity/20261002/subsets.json'
    manifest = json.loads(subset_path.read_text())
    assert manifest['test_manifest_sha256'] == sha(ROOT/'configs/test_manifest.json')
    views = subsets(manifest, json.loads((ROOT/'configs/test_manifest.json').read_text()))
    out = dict(kind='saved_blackbox_subset_sensitivity', independent_verification_approval=False,
               original_results_unchanged=True, subset_manifest_sha256=sha(subset_path),
               subset_counts={k:len(v) for k,v in views.items()}, square={}, surfree={})
    for role in ('original','trained'):
        for budget,seeds in ((200,(2026,)),(1000,(2026,2027,2028))):
            all_rows=[]
            for seed in seeds:
                folder=ROOT/f'results/extensions/square/cnn_{role}_q{budget}_s{seed}_20261003'
                rows=list(csv.DictReader((folder/'eps_0.03.csv').open(newline='')))
                all_rows.append(rows)
                out['square'][folder.name]=dict(run_report_sha256=sha(folder/'run.json'),
                    views={k:metric(rows,keep,lambda r:r['attacked_pred']!=r['true_index']) for k,keep in views.items()})
            failed={r['relative_path'] for rows in all_rows for r in rows if r['attacked_pred']!=r['true_index']}
            out['square'][f'{role}_q{budget}_seed_union']=dict(
                views={k:metric(all_rows[0],keep,lambda r:r['relative_path'] in failed) for k,keep in views.items()})
        folder=ROOT/f'results/extensions/surfree/cnn_{role}_q200_s2026_20261003'
        rows=[json.loads(line) for line in (folder/'samples.jsonl').read_text().splitlines()]
        out['surfree'][role]=dict(run_report_sha256=sha(folder/'run.json'),thresholds={
            str(t):{k:metric(rows,keep,lambda r:r['successful'] and r['rms']<=t) for k,keep in views.items()}
            for t in (.01,.03,.05)})
    out['limitations']=[
        'Descriptive reaggregation of existing predictions; no new independent held-out evaluation.',
        'Source-train overlap does not establish historical baseline training membership.',
        'Unique RGB keeps the lexicographically first path per exact duplicate group; near duplicates are not checked.',
        'The trained checkpoint used filtered training data; exclusions do not remove possible historical baseline exposure.',
        'Square Linf .03 and SurFree RMS cutoffs are different constraints; seed union combines separate attacks.']
    return out


if __name__=='__main__':
    print(json.dumps(generate(),indent=2,allow_nan=False))
