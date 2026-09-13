"""Export a read-only, audited replay snapshot. Never runs inference or attacks."""
import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('public/evidence'))
    args=p.parse_args();repo=args.repo.resolve();out=args.output.resolve()
    if repo==out or repo in out.parents:
        raise ValueError('Output must be outside the research checkout')
    # Require tracked source to match the cited commit.
    subprocess.run(['git','diff','--exit-code','HEAD'],cwd=repo,check=True,stdout=subprocess.DEVNULL)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    sys.path.insert(0,str(repo/'src'))
    from adversarial_ai.audit.runner import run_full_audit
    report=run_full_audit(repo_root=repo)
    if report['status']!='PASSED': raise ValueError('Research audit failed')
    out.mkdir(parents=True,exist_ok=True);(out/'images').mkdir(exist_ok=True)
    hashes={}
    def read(path):
        raw=(repo/path).read_bytes();hashes[str(path)]=hashlib.sha256(raw).hexdigest()
        return raw
    def rows(path):return list(csv.DictReader(read(path).decode('utf-8-sig').splitlines()))
    prov=Path('results/attacks/provisional')
    read(Path('configs/test_manifest.json'));read(Path('docs/EXPERIMENT_CONTRACT.md'))
    read(Path('src/adversarial_ai/evaluation/fgsm_evaluation.py'))
    comparison=rows(prov/'fgsm_comparison_summary.csv')
    models=list(dict.fromkeys(r['model'] for r in comparison))
    epsilons=sorted({float(r['epsilon']) for r in comparison})
    all_rows={};clean={};results=[];class_names=[]
    def count(rs):
        n=len(rs);d=sum(r['clean_predicted_label']==r['true_label'] for r in rs)
        successes=sum(r['clean_predicted_label']==r['true_label'] and r['adversarial_predicted_label']!=r['true_label'] for r in rs)
        return dict(n=n,cleanCorrect=d,robustCorrect=sum(r['adversarial_predicted_label']==r['true_label'] for r in rs),successes=successes,asr=successes/d if d else None)
    for model in models:
        clean[model]=rows(Path('results/clean')/('cnn_baseline_eval.csv' if model=='cnn' else 'mobilenet_eval.csv'))
        metadata=json.loads(read(prov/f'fgsm_{model}_metadata.json'))
        if sorted(metadata['epsilons'])!=epsilons or metadata['attack']!='untargeted FGSM, exactly one step':raise ValueError('Unsupported attack metadata')
        for eps in epsilons:
            rs=rows(prov/f'fgsm_{model}_eps_{eps:g}_samples.csv');all_rows[model,eps]=rs
            names=list(dict.fromkeys(r['true_label'] for r in rs))
            if class_names and names!=class_names:raise ValueError('Class order mismatch')
            class_names=names
            for i,r in enumerate(rs):
                if r['relative_path'].replace('\\','/')!=clean[model][i]['relative_path'].replace('\\','/'):raise ValueError('Sample order mismatch')
            c=count(rs);ref=report['summary']['fgsm_provisional'][model+'_epsilons'][str(eps)]
            if c['successes']!=ref['attack_successes'] or c['cleanCorrect']!=ref['asr_denominator']:raise ValueError('Aggregate mismatch')
            results.append(dict(model=model,epsilon=eps,**c,classes=[dict(name=name,**count([r for r in rs if r['true_label']==name])) for name in names]))
    samples=[]
    paths=sorted((repo/prov/'samples').glob('*.png'),key=lambda p:('success' not in p.name,p.name))
    for path in paths:
        # Only committed images can be exported. Untracked research material is never copied.
        rel=path.relative_to(repo)
        if subprocess.run(['git','ls-files','--error-unmatch',str(rel)],cwd=repo,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:continue
        match=re.fullmatch(r'(cnn|mobilenet)_eps_([0-9.]+)_(success|failure)_(\d+)\.png',path.name)
        if not match:raise ValueError('Unrecognized sample image')
        model,eps,category,index=match.groups();eps=float(eps);index=int(index)
        r=all_rows[model,eps][index];cr=clean[model][index]
        if r['clean_correct']!='True' or (r['attack_success']=='True')!=(category=='success'):raise ValueError('Sample filename/category mismatch')
        raw=read(rel)
        # PNG IHDR; image bytes stay untouched. CSS exposes the plotted panels.
        if raw[:8]!=b'\x89PNG\r\n\x1a\n':raise ValueError('Not PNG')
        width=int.from_bytes(raw[16:20],'big');height=int.from_bytes(raw[20:24],'big')
        if (width,height)!=(1542,556):raise ValueError('Review panel coordinates for changed plot dimensions')
        (out/'images'/path.name).write_bytes(raw)
        score=float(cr[f"prob_{cr['predicted_index']}_{cr['predicted_label']}"])
        samples.append(dict(id=path.stem,model=model,epsilon=eps,path=r['relative_path'].replace('\\','/'),truth=r['true_label'],cleanPrediction=r['clean_predicted_label'],attackPrediction=r['adversarial_predicted_label'],cleanScore=score,success=category=='success',asset='/evidence/images/'+path.name,sourceUrl=f'https://github.com/heechan9/AdversarialAI_Security/blob/{sha}/{rel}',width=width,height=height,panels=[dict(x=x,y=80,size=460) for x in [16,541,1067]]))
    if not samples:raise ValueError('No committed visual samples')
    data=dict(schema='maris-evidence/v1',sourceCommit=sha,repoUrl='https://github.com/heechan9/AdversarialAI_Security',total=len(clean[models[0]]),models=models,epsilons=epsilons,classNames=class_names,samples=samples,results=results)
    def save(name,value):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save('data.json',data)
    save('provenance.json',dict(schema='maris-provenance/v1',source_commit=sha,source_sha256=hashes,export_sha256=hashlib.sha256((out/'data.json').read_bytes()).hexdigest(),research_audit_status=report['status'],unverified_scopes=report['unverified_scopes'],mode='recorded replay; no inference',image_presentation='Byte-identical committed comparison plots. CSS crops plotted input panels, not raw original image files. Panel coordinates visually inspected.',attack_score='Not recorded in per-sample FGSM CSV; never synthesized.'))
    print(json.dumps(dict(total=data['total'],samples=len(samples),rows=len(results),audit=report['status'],source=sha)))

if __name__=='__main__':main()
