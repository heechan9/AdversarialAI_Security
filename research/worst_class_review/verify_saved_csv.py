"""Independent raw saved-CSV recount; no audit-code imports or model execution."""
import csv
import json
from pathlib import Path
import subprocess
import sys

root=Path(sys.argv[1]).resolve()
packet=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
if subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()!=packet['source_commit']:
    raise SystemExit('FAIL: source commit mismatch')
if subprocess.check_output(['git','status','--porcelain','--','results','configs','src'],cwd=root,text=True):
    raise SystemExit('FAIL: source checkout is not pristine')
checked=0
for model in ('cnn','mobilenet'):
    for eps in (0.,.01,.03,.05):
        path=root/f'results/attacks/provisional/fgsm_{model}_eps_{eps:g}_samples.csv'
        with path.open(encoding='utf-8',newline='') as handle:
            raw=list(csv.DictReader(handle))
        if len(raw)!=781:
            raise SystemExit(f'FAIL: expected 781 saved rows for {model} epsilon {eps}')
        for entry in [r for r in packet['classes'] if r['model']==model and r['epsilon']==eps]:
            group=[r for r in raw if r['true_label']==entry['class_name']]
            n=len(group)
            d=sum(r['clean_predicted_label']==r['true_label'] for r in group)
            a=sum(r['adversarial_predicted_label']==r['true_label'] for r in group)
            s=sum(r['clean_predicted_label']==r['true_label'] and r['adversarial_predicted_label']!=r['true_label'] for r in group)
            recovered=sum(r['clean_predicted_label']!=r['true_label'] and r['adversarial_predicted_label']==r['true_label'] for r in group)
            if (n,d,n-d,s,a,recovered)!=tuple(entry[k] for k in ('N','D','B','S','attacked_correct','clean_wrong_to_attacked_correct')):
                raise SystemExit(f"FAIL: saved count mismatch for {model} epsilon {eps} class {entry['class_name']}")
            checked+=1
if checked!=80:
    raise SystemExit('FAIL: expected exactly 80 class rows')
print(json.dumps({'class_rows_recounted_from_saved_predictions':checked,'conditions':8,'status':'PASS','model_inference':'NOT_RUN'}))
