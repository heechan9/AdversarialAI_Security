"""Paired saved-result comparison; does not establish general robustness."""
import argparse
import csv
import json
import math
from pathlib import Path
from square_saved_audit import audit


def compare(plain, defended, epsilon):
    for folder in (plain,defended):
        audit(folder)
    reports=[json.loads((p/'run.json').read_text()) for p in (plain,defended)]
    for key in ('model_sha256','manifest_sha256','classes_sha256','tensorflow','keras','numpy','environment'):
        if reports[0][key]!=reports[1][key]:
            raise ValueError('comparison mismatch: '+key)
    for key in ('model','per_class','max_queries','p_init','seed','batch_size'):
        if reports[0]['settings'][key]!=reports[1]['settings'][key]:
            raise ValueError('settings mismatch: '+key)
    if reports[0]['settings']['defense']!='none' or reports[1]['settings']['defense']=='none':
        raise ValueError('expected plain and defended runs')
    rows=[]
    for folder,report in zip((plain,defended),reports):
        condition=next(c for c in report['conditions'] if c['epsilon']==epsilon)
        rows.append(list(csv.DictReader((folder/condition['csv']).open())))
    if [r['relative_path'] for r in rows[0]]!=[r['relative_path'] for r in rows[1]]:
        raise ValueError('sample order differs')
    result={'epsilon':epsilon,'samples':len(rows[0]),'runs':[p.name for p in (plain,defended)],
            'interpretation':'paired descriptive comparison at one attack budget; no deployment safety claim'}
    for phase in ('clean','attacked'):
        a=[r[phase+'_pred']==r['true_index'] for r in rows[0]]
        b=[r[phase+'_pred']==r['true_index'] for r in rows[1]]
        gained=sum(not x and y for x,y in zip(a,b))
        lost=sum(x and not y for x,y in zip(a,b))
        discordant=gained+lost
        p=min(1.,2*sum(math.comb(discordant,k) for k in range(min(gained,lost)+1))/2**discordant) if discordant else 1.
        result[phase]={'plain_correct':sum(a),'defended_correct':sum(b),
            'defended_minus_plain_percentage_points':100*(sum(b)-sum(a))/len(a),
            'gained':gained,'lost':lost,'mcnemar_exact_two_sided_p':p}
    common=[(a,b) for a,b in zip(*rows) if a['clean_pred']==a['true_index'] and b['clean_pred']==b['true_index']]
    result['common_clean_correct']={'samples':len(common),
        'plain_attack_successes':sum(a['attacked_pred']!=a['true_index'] for a,b in common),
        'defended_attack_successes':sum(b['attacked_pred']!=b['true_index'] for a,b in common)}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plain',type=Path);p.add_argument('defended',type=Path)
    p.add_argument('--epsilon',type=float,default=.03)
    args=p.parse_args()
    print(json.dumps(compare(args.plain,args.defended,args.epsilon),indent=2))
