"""Wait for existing full evaluations, then train/evaluate MobileNet serially.

The queue does not publish results or claim independent approval. RUNNING input
reports alone do not establish liveness; operator status must check processes.
"""
import datetime,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/extensions/queues/remaining-20261004'
DEPENDENCIES=[
 ('bim',ROOT/'results/extensions/iterative/bim-complete-20261004/run.json','COMPLETED_NOT_INDEPENDENT_APPROVAL'),
 ('pgd',ROOT/'results/extensions/iterative/pgd-complete-20261004/run.json','COMPLETED_NOT_INDEPENDENT_APPROVAL'),
 ('jsma',ROOT/'results/extensions/jsma/cnn-full-20261004/run.json','FULL_COVERAGE_NOT_ROBUSTNESS_PROOF')]

def main():
 OUT.mkdir(parents=True,exist_ok=False)
 state=dict(status='WAITING_FOR_EVALUATIONS',independent_verification_approval=False,
  started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  prior_training_attempt='mobilenet-pgd7-20261004: process stopped for memory pressure before first completed epoch; raw report RUNNING is stale',
  settings=dict(model='mobilenet',epochs=3,epsilon=.03,step_size=.005,steps=7,seed=2026,batch_size=8,learning_rate=1e-5))
 def save():
  state['updated_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
  p=OUT/'queue.json.tmp';p.write_text(json.dumps(state,indent=2)+'\n');p.replace(OUT/'queue.json')
 def run(stage,args):
  state['status']=stage;save()
  env=os.environ.copy();env.update(PYTHONPATH=str(ROOT/'src')+':'+str(ROOT),TF_NUM_INTRAOP_THREADS='2',TF_NUM_INTEROP_THREADS='1')
  with (OUT/(stage+'.log')).open('x') as log:
   subprocess.run([sys.executable,*args],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 try:
  while True:
   states={name:json.loads(path.read_text())['status'] for name,path,_ in DEPENDENCIES}
   state['dependencies']=states;save()
   if any(v in ('ERROR','INTERRUPTED') for v in states.values()):raise RuntimeError('dependency did not complete')
   if all(states[name]==expected for name,_,expected in DEPENDENCIES):break
   time.sleep(30)
  from verification.iterative_result_audit import audit
  for name,path,_ in DEPENDENCIES[:2]:
   result=audit(path.parent,ROOT)
   if result['result']!='FULL_OUTPUTS_CONSISTENT':raise RuntimeError('incomplete '+name)
   (OUT/(name+'-audit.json')).write_text(json.dumps(result,indent=2)+'\n')
  trained=ROOT/'results/extensions/adversarial_training/mobilenet-pgd7-20261004-serial'
  run('TRAINING',['-m','adversarial_ai.training.adversarial_training','--model','mobilenet',
   '--train-dir','data/train-prepared/images','--validation-dir','data/valid','--test-dir','data/test',
   '--epochs','3','--epsilon','.03','--step-size','.005','--steps','7','--seed','2026','--batch-size','8',
   '--learning-rate','.00001','--run-id',trained.name])
  run('TEST_EVALUATION',['verification/mobilenet_pgd7_test_evaluation.py','--trained-dir',str(trained),
   '--test-dir','data/test','--output-dir','results/extensions/mobilenet_adversarial_20261004'])
  state['status']='COMPLETED_AWAITING_RESULT_AUDIT_AND_PUBLICATION';save()
 except BaseException as exc:
  state['status']='INTERRUPTED' if isinstance(exc,KeyboardInterrupt) else 'ERROR'
  state['error']=str(exc);save();raise
if __name__=='__main__':main()
