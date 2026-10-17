import os,json,csv,hashlib,subprocess,datetime
from pathlib import Path
import numpy as np
import tensorflow as tf
from adversarial_ai.attacks.iterative import generate_iterative
from adversarial_ai.attacks.fgsm import infer_from_logits
from adversarial_ai.evaluation.integrity import validate_reproducibility_manifest,sha256_file
root=Path.cwd(); work=root.parent
import argparse
parser=argparse.ArgumentParser(description='MobileNetV2 clean and PGD7 test comparison; run from the pinned repository root')
parser.add_argument('--trained-dir',type=Path,required=True)
parser.add_argument('--test-dir',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args()
trained=args.trained_dir
out=args.output_dir
if any(p.is_symlink() for p in [out,*out.parents]):raise ValueError('unsafe output path')
out.mkdir(parents=True,exist_ok=False)
report={'status':'RUNNING','scope':'MobileNetV2 clean and PGD7; no filters; not comprehensive robustness evaluation','samples':781,'epsilon':0.03,'steps':7,'step_size':0.005,'restarts':1,'seed':2026,'batch_size':8,'models':{},'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'tensorflow':tf.__version__,'keras':tf.keras.__version__,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
def save():
 p=out/'evaluation.json.tmp';p.write_text(json.dumps(report,indent=2));p.replace(out/'evaluation.json')
save()
try:
 report['devices']=[d.device_type for d in tf.config.list_physical_devices()]
 training=json.loads((trained/'training.json').read_text())
 assert training['status']=='TRAINED_NOT_TEST_EVALUATED'
 assert training['settings']['model']=='mobilenet'
 report['training_report_sha256']=sha256_file(trained/'training.json')
 report['numpy']=np.__version__
 report['environment']={k:os.environ.get(k) for k in ('TF_ENABLE_ONEDNN_OPTS','TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS')}
 report['independent_verification_approval']=False
 classes=json.loads((root/'configs/classes.json').read_text());names=[classes[str(i)] for i in range(10)]
 gen=tf.keras.preprocessing.image.ImageDataGenerator(rescale=1./255).flow_from_directory(str(args.test_dir),classes=names,target_size=(224,224),batch_size=8,shuffle=False)
 assert gen.n==781
 validate_reproducibility_manifest(manifest_path=root/'configs/test_manifest.json',model_path=Path('models/mobilenet_finetuned.h5'),dataset_filenames=gen.filenames,data_dir=args.test_dir)
 report['test_manifest_sha256']=sha256_file(root/'configs/test_manifest.json')
 for kind,path,expected in [('original',root/'models/mobilenet_finetuned.h5',training['source_model_sha256']),('trained',trained/'best.keras',training['trained_model_sha256'])]:
  assert sha256_file(path)==expected
  tf.keras.utils.set_random_seed(2026)
  model=tf.keras.models.load_model(path,compile=False);weights=[v.numpy().copy() for v in model.weights];rows=[]
  for batch in range(len(gen)):
   x,y=gen[batch];truth=y.argmax(1)
   adv=generate_iterative(model,x,y,0.03,step_size=0.005,steps=7,attack='pgd',restarts=1,seed=2026+batch,from_logits=infer_from_logits(model))
   clean=np.asarray(model(x,training=False)); attacked=np.asarray(model(adv,training=False))
   assert np.isfinite(clean).all() and np.isfinite(attacked).all()
   delta=np.max(np.abs(np.asarray(adv)-x),axis=(1,2,3));assert delta.max()<=0.030001
   for j in range(len(x)):rows.append({'relative_path':gen.filenames[batch*8+j],'true_index':int(truth[j]),'clean_pred':int(clean[j].argmax()),'pgd_pred':int(attacked[j].argmax()),'linf':float(delta[j])})
   if (batch+1)%10==0 or batch+1==len(gen):print(kind,'batch',batch+1,'/',len(gen),flush=True)
  assert len(rows)==781 and len({r['relative_path'] for r in rows})==781
  assert all(np.array_equal(a,v.numpy()) for a,v in zip(weights,model.weights))
  p=out/(kind+'.csv')
  with p.open('x',newline='') as f:
   writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
  clean_count=sum(r['clean_pred']==r['true_index'] for r in rows);adv_count=sum(r['pgd_pred']==r['true_index'] for r in rows)
  successes=sum(r['clean_pred']==r['true_index'] and r['pgd_pred']!=r['true_index'] for r in rows)
  report['models'][kind]={'sha256':expected,'samples':781,'clean_correct':clean_count,'pgd_correct':adv_count,'clean_accuracy':clean_count/781,'pgd_accuracy':adv_count/781,'attack_success_rate':successes/clean_count if clean_count else None,'csv_sha256':sha256_file(p)};save()
  print(kind,json.dumps(report['models'][kind]),flush=True)
  del model;tf.keras.backend.clear_session()
 report['status']='COMPLETED';report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save()
 print('FINAL_EVALUATION_COMPLETE',json.dumps(report),flush=True)
except BaseException as e:
 report['status']='ERROR';report['error']=str(e);save();raise
