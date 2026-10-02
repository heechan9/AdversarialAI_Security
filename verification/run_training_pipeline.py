"""Run configured adversarial training then separate full trained-model evaluations."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from verification.iterative_result_audit import audit


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',choices=['cnn','mobilenet'],required=True)
    parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--valid',type=Path,required=True)
    parser.add_argument('--test',type=Path,required=True)
    parser.add_argument('--run-prefix',required=True)
    a=parser.parse_args();root=Path(__file__).resolve().parents[1]
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,39}',a.run_prefix):raise ValueError('invalid run prefix')
    prepared=a.prepared.resolve();preparation=json.loads((prepared/'preparation.json').read_text())
    if preparation['status']!='PREPARED_EXACT_AUDIT_ONLY' or preparation['source_count']!=8067:
        raise ValueError('complete-data preparation is required')
    gate=json.loads((prepared/'split-audit.json').read_text());rows=gate['splits']['train']
    images=prepared/'images'
    actual={p.relative_to(images).as_posix() for p in images.rglob('*') if p.is_file()}
    if len(rows)!=preparation['retained_count'] or actual!={r['path'] for r in rows}:
        raise ValueError('prepared training inventory changed')
    for row in rows:
        if digest(images/row['path'])!=row['sha256']:raise ValueError('prepared training image changed')
    run_id=f'{a.run_prefix}-{a.model}'
    output=root/'results/extensions/pipelines'/run_id
    if any(p.is_symlink() for p in (output,*output.parents)):raise ValueError('unsafe output')
    output.mkdir(parents=True,exist_ok=False)
    state={'kind':'configured_training_and_evaluation_pipeline','model':a.model,'status':'RUNNING',
           'started_at':datetime.now(timezone.utc).isoformat(),'completed_stages':[],
           'preparation_sha256':digest(prepared/'preparation.json'),'near_duplicate_checked':False}
    def save():
        temp=output/'pipeline.json.tmp';temp.write_text(json.dumps(state,indent=2)+'\n');temp.replace(output/'pipeline.json')
    env=os.environ.copy();env['PYTHONPATH']=str(root/'src')
    def execute(module,args,stage):
        state['active_stage']=stage;save()
        subprocess.run([sys.executable,'-m',module,*map(str,args)],cwd=root,env=env,check=True)
        state['completed_stages'].append(stage);save()
    try:
        execute('adversarial_ai.training.adversarial_training',[
            '--model',a.model,'--train-dir',images,'--validation-dir',a.valid.resolve(),
            '--test-dir',a.test.resolve(),'--epochs',3,'--epsilon',.03,'--step-size',.005,
            '--steps',7,'--seed',2026,'--batch-size',32,'--learning-rate',.00001,
            '--run-id',run_id],'training')
        trained=root/'results/extensions/adversarial_training'/run_id
        report=json.loads((trained/'training.json').read_text());model=trained/'best.keras'
        if report['status']!='TRAINED_NOT_TEST_EVALUATED' or digest(model)!=report['trained_model_sha256']:
            raise ValueError('training completion or model identity invalid')
        state['trained_model_sha256']=digest(model);save()
        for attack,steps,restarts,batch,seed in [('bim',10,1,32,0),('pgd',20,5,16,2026)]:
            evaluation_id=f'{run_id}-{attack}'
            execute('adversarial_ai.evaluation.iterative_evaluation',[
                '--attack',attack,'--steps',steps,'--step-size',.005,'--restarts',restarts,
                '--seed',seed,'--batch-size',batch,'--run-id',evaluation_id,'--data-dir',a.test.resolve(),
                '--trained-model',model,'--trained-model-sha256',state['trained_model_sha256'],
                '--trained-model-kind',a.model],attack)
            checked=audit(root/'results/extensions/iterative'/evaluation_id,root)
            if checked['result']!='FULL_OUTPUTS_CONSISTENT':raise ValueError('incomplete trained-model evaluation')
            (output/f'{attack}-audit.json').write_text(json.dumps(checked,indent=2)+'\n')
        state['status']='COMPLETED_NOT_INDEPENDENT_APPROVAL'
    except BaseException as exc:
        state['status']='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'ERROR'
        state['error']=f'{type(exc).__name__}: {exc}';raise
    finally:
        state['finished_at']=datetime.now(timezone.utc).isoformat();save()


if __name__=='__main__':main()
