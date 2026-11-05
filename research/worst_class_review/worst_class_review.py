"""Descriptive worst-class review of an audited saved-row packet, not a safety certification."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path

PINNED_SOURCE = '75defef0d69c1741025306e0150c770e84b23a30'
PINNED_PACKET = 'e5b6a44b7e4906bba933de7573181c05a6893b5d473afa9664a2d4ed24a4793b'  # Set to the already-delivered immutable packet JSON digest below.


def summarize(rows):
    if not rows or len({r['class_name'] for r in rows}) != len(rows):
        raise ValueError('empty or duplicate class coverage')
    for r in rows:
        n,d,b,s,a = (r[k] for k in ('N','D','B','S','attacked_correct'))
        if any(type(v) is not int for v in (n,d,b,s,a)) or not (n>0 and 0<=s<=d<=n and 0<=a<=n and b==n-d):
            raise ValueError('invalid counts')
        recovered=a-d+s
        if not 0<=recovered<=b or r['clean_wrong_to_attacked_correct']!=recovered:
            raise ValueError('invalid transition accounting')
        if r['ASR']!=(s/d if d else None) or r['attacked_accuracy']!=a/n:
            raise ValueError('inconsistent derived rate')
    def extreme(numerator, denominator, high=False):
        values=[(Fraction(r[numerator],r[denominator]),r['class_name']) for r in rows if r[denominator]]
        if not values:return {'value':None,'classes':[]}
        value=(max if high else min)(v for v,_ in values)
        return {'value':float(value),'classes':sorted(name for v,name in values if v==value)}
    attacked=extreme('attacked_correct','N')
    fields=('class_name','N','D','B','S','ASR','attacked_correct','clean_wrong_to_attacked_correct')
    return dict(minimum_clean_accuracy=extreme('D','N'),minimum_attacked_accuracy=attacked,
        maximum_conditional_ASR=extreme('S','D',True),
        undefined_ASR_classes=sorted(r['class_name'] for r in rows if r['D']==0),
        worst_attacked_details=[{k:r[k] for k in fields} for r in sorted(rows,key=lambda r:r['class_name']) if r['class_name'] in attacked['classes']])


def review(packet_path):
    raw=packet_path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=PINNED_PACKET:
        raise ValueError('input differs from the previously audited packet; re-audit before reviewing')
    packet=json.loads(raw)
    if packet['source_commit']!=PINNED_SOURCE or packet['checks']!={'conditions':8,'class_rows':80,'full_saved_evidence_audit':'PASSED','historical_v1_5_claims_passed':9}:
        raise ValueError('unexpected baseline or audit status')
    rows=packet['classes']
    expected={(m,e) for m in ('cnn','mobilenet') for e in (0.,.01,.03,.05)}
    if {(r['model'],r['epsilon']) for r in rows}!=expected or len(rows)!=80:
        raise ValueError('condition coverage mismatch')
    conditions=[]
    for model,epsilon in sorted(expected):
        group=[r for r in rows if (r['model'],r['epsilon'])==(model,epsilon)]
        if len(group)!=10 or sum(r['N'] for r in group)!=781:raise ValueError('class/sample coverage mismatch')
        conditions.append(dict(model=model,epsilon=epsilon,**summarize(group)))
    return dict(source_commit=PINNED_SOURCE,input_sha256=PINNED_PACKET,conditions=conditions,
        evidence_scope='Descriptive saved-row worst-class screening only; not safety certification or independent inference.',
        limitations=packet['limitations']+['No operational acceptance threshold, cost weighting, statistical worst-case guarantee, or causal explanation is inferred.'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('packet',type=Path);p.add_argument('output',type=Path)
    args=p.parse_args(); result=review(args.packet)
    with args.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False)
    print('8 conditions screened; output created without overwriting existing evidence')
