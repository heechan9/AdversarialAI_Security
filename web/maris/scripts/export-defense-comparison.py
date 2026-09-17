"""Export only independently audited, experimental defense records. No inference."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repo',type=Path,required=True)
parser.add_argument('--source-commit',required=True,help='Published Git commit containing these exact audited artifacts')
a=parser.parse_args()
if len(a.source_commit)!=40 or any(c not in '0123456789abcdef' for c in a.source_commit):
    raise ValueError('invalid source commit')
methods=[];hashes={};audits={}
for key,name,description in [('gaussian','가우시안 필터','가까운 픽셀에 더 큰 비중을 두는 고정 3×3 필터'),('mean','평균 필터','주변 픽셀을 같은 비중으로 섞는 고정 3×3 필터')]:
    path=a.repo/f'scripts/audit_{key}_defense.py'
    spec=importlib.util.spec_from_file_location('audit_'+key,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    root=a.repo/f'results/defenses/experimental/{key}_run_01';audits[key]=m.audit(a.repo,root)
    raw=(root/'summary.json').read_bytes();rows=json.loads(raw)
    # Keep all models and epsilon values. Compact export omits class metrics only.
    methods.append(dict(id=key,name=name,description=description,sourceUrl=f'https://github.com/heechan9/AdversarialAI_Security/tree/{a.source_commit}/results/defenses/experimental/{key}_run_01',results=[{k:r[k] for k in ('model','epsilon','overall')} for r in rows]))
    hashes[key]=dict(summary_sha256=hashlib.sha256(raw).hexdigest(),original_zip_sha256=hashlib.sha256((root/'original_bundle.zip').read_bytes()).hexdigest())
conditions=[{(r['model'],r['epsilon']) for r in m['results']} for m in methods]
assert conditions[0]==conditions[1]
out=Path(__file__).resolve().parents[1]/'public/evidence';out.mkdir(parents=True,exist_ok=True)
d=dict(status='experimental',mode='recorded replay; no inference',models=sorted({m for m,e in conditions[0]}),epsilons=sorted({e for m,e in conditions[0]}),methods=methods)
raw=(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode();(out/'defense-comparison.json').write_bytes(raw)
p=dict(source_commit=a.source_commit,export_sha256=hashlib.sha256(raw).hexdigest(),source_hashes=hashes,audits=audits,status='experimental',limits='Artifact audit only. No independent model inference, raw arrays or H5 verification.')
(out/'defense-comparison-provenance.json').write_text(json.dumps(p,indent=2)+'\n')
print('Exported both audited defenses; all recorded model/epsilon conditions.')
