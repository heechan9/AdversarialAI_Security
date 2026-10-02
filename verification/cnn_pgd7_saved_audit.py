"""Recalculate the saved CNN comparison; no TensorFlow or private inputs needed."""
import csv,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/extensions/cnn_adversarial_20261002'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 report=json.loads((OUT/'evaluation.json').read_text())
 train=json.loads((OUT/'training.json').read_text())
 manifest=ROOT/'configs/test_manifest.json'
 assert digest(manifest)==report['test_manifest_sha256']
 labels=json.loads((ROOT/'configs/classes.json').read_text())
 lookup={v:int(k) for k,v in labels.items()}
 expected={r['relative_path']:lookup[r['label']] for r in json.loads(manifest.read_text())['test_files']}
 assert report['status']=='COMPLETED' and report['samples']==781
 assert (report['epsilon'],report['steps'],report['step_size'],report['restarts'])==(.03,7,.005,1)
 assert len(train['epochs'])==3 and train['best_epoch']==3
 for kind in ('original','trained'):
  path=OUT/(kind+'.csv');s=report['models'][kind]
  assert digest(path)==s['csv_sha256']
  rows=list(csv.DictReader(path.open()))
  assert len(rows)==781 and len({r['relative_path'] for r in rows})==781
  assert {r['relative_path']:int(r['true_index']) for r in rows}==expected
  for r in rows:
   assert all(0<=int(r[k])<10 for k in ('true_index','clean_pred','pgd_pred'))
   assert math.isfinite(float(r['linf'])) and 0<=float(r['linf'])<=.030001
  clean=sum(r['true_index']==r['clean_pred'] for r in rows)
  pgd=sum(r['true_index']==r['pgd_pred'] for r in rows)
  success=sum(r['true_index']==r['clean_pred'] and r['true_index']!=r['pgd_pred'] for r in rows)
  assert (clean,pgd)==(s['clean_correct'],s['pgd_correct'])
  assert math.isclose(clean/781,s['clean_accuracy'],abs_tol=1e-12)
  assert math.isclose(pgd/781,s['pgd_accuracy'],abs_tol=1e-12)
  assert math.isclose(success/clean,s['attack_success_rate'],abs_tol=1e-12)
  assert s['sha256']==train['source_model_sha256' if kind=='original' else 'trained_model_sha256']
 print('PASS: 2 CSVs, 781 rows each; manifest, labels, hashes, accuracy, ASR, perturbation bounds and model identities')
if __name__=='__main__':main()
