"""Recompute fixed-budget, multi-seed CNN black-box comparisons."""
import csv
import json
from pathlib import Path
from square_saved_audit import audit as audit_square
from surfree_saved_audit import audit as audit_surfree

ROOT=Path(__file__).resolve().parents[1]


def generate():
    base=ROOT/'results/extensions/square'
    reports={};rows={};out={'square':{},'surfree':{}}
    for budget,seeds in ((200,(2026,)),(1000,(2026,2027,2028))):
        for role in ('original','trained'):
            runs=[];attack_rows=[]
            for seed in seeds:
                folder=base/f'cnn_{role}_q{budget}_s{seed}_20261003'
                audit_square(folder)
                r=json.loads((folder/'run.json').read_text())
                expected_role='original' if role=='original' else 'adversarially_trained'
                assert r['model_role']==expected_role
                assert r['settings']['max_queries']==budget and r['settings']['seed']==seed
                assert r['settings']['per_class']==0 and r['settings']['batch_size']==20
                assert r['settings']['defense']=='none'
                c=next(c for c in r['conditions'] if c['epsilon']==.03)
                rr=list(csv.DictReader((folder/c['csv']).open()))
                if attack_rows:
                    assert [(x['relative_path'],x['clean_pred']) for x in rr]==[(x['relative_path'],x['clean_pred']) for x in attack_rows[0]]
                attack_rows.append(rr)
                runs.append(dict(seed=seed,run=folder.name,metrics=c['metrics']))
                reports[(role,budget,seed)]=r
            first=attack_rows[0]
            rows[(role,budget)]=attack_rows
            clean=sum(r['clean_pred']==r['true_index'] for r in first)
            worst=sum(all(rr[i]['attacked_pred']==rr[i]['true_index'] for rr in attack_rows) for i in range(len(first)))
            out['square'][f'{role}_q{budget}']=dict(runs=runs,union_across_seeds=dict(
                samples=len(first),clean_correct=clean,attacked_correct=worst,accuracy=worst/len(first),
                asr=(clean-worst)/clean,successes=clean-worst,denominator=clean))
        for seed in seeds:
            a=reports[('original',budget,seed)];b=reports[('trained',budget,seed)]
            for key in ('environment','tensorflow','keras','numpy','manifest_sha256','classes_sha256'):
                assert a[key]==b[key],key
        a=rows[('original',budget)];b=rows[('trained',budget)]
        assert [r['relative_path'] for r in a[0]]==[r['relative_path'] for r in b[0]]
        common=[i for i,(x,y) in enumerate(zip(a[0],b[0])) if x['clean_pred']==x['true_index'] and y['clean_pred']==y['true_index']]
        out['square'][f'paired_q{budget}']=dict(common_clean_correct=len(common),
            original_successes=sum(any(rr[i]['attacked_pred']!=rr[i]['true_index'] for rr in a) for i in common),
            trained_successes=sum(any(rr[i]['attacked_pred']!=rr[i]['true_index'] for rr in b) for i in common))
    sur_reports=[]
    for role in ('original','trained'):
        folder=ROOT/f'results/extensions/surfree/cnn_{role}_q200_s2026_20261003'
        audit_surfree(folder);r=json.loads((folder/'run.json').read_text())
        assert r['settings']['model_role']==role and r['settings']['max_queries']==200
        assert r['settings']['per_class']==0 and r['settings']['seed']==2026
        sur_reports.append(r)
        out['surfree'][role]=dict(run=folder.name,metrics=r['metrics'])
    for key in ('environment','tensorflow','keras','numpy','torch','manifest_sha256','classes_sha256','upstream_parameters','upstream_commit'):
        assert sur_reports[0][key]==sur_reports[1][key],key
    out['limitations']=['Square: Linf .03; 1000-query schedules are not prefixes of 200-query schedules.',
        'SurFree: top-1 L2 search, 200 total queries including initialization; RMS is not Linf.',
        'Seed union is worst observed per image across 3 runs, not a single 1000-query run.',
        'No independent model replay, physical maritime safety claim or robustness certificate.']
    return out


if __name__=='__main__':print(json.dumps(generate(),indent=2))
