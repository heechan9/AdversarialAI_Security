import csv
import hashlib
import json
from pathlib import Path
import pytest
from verification.full_extension_audit import audit_mobile, audit_all, digest


def write(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def evidence(tmp_path):
    root=tmp_path; (root/'configs').mkdir();t=root/'training';e=root/'evaluation';t.mkdir();e.mkdir()
    manifest={'models':[{'path':'models/mobilenet_finetuned.h5','sha256':'a'*64}],
              'test_files':[{'relative_path':f'c/{i}.png','sha256':hashlib.sha256(f'test{i}'.encode()).hexdigest()} for i in range(781)]}
    write(root/'configs/test_manifest.json',manifest);write(root/'configs/classes.json',{'0':'c'})
    splits={name:[{'path':f'c/{i}.png','sha256':hashlib.sha256(f'{name}{i}'.encode()).hexdigest(),
                   'pixel_sha256':hashlib.sha256(f'pixel{name}{i}'.encode()).hexdigest()} for i in range(n)]
            for name,n in [('train',6147),('validation',689),('test',781)]}
    write(t/'split-audit.json',{'manifest_sha256':digest(root/'configs/test_manifest.json'),'splits':splits})
    (t/'best.keras').write_bytes(b'fixture weights: hash check only')
    training={'status':'TRAINED_NOT_TEST_EVALUATED','source_model_sha256':'a'*64,
              'trained_model_sha256':digest(t/'best.keras'),'split_audit_sha256':digest(t/'split-audit.json'),
              'settings':dict(model='mobilenet',epochs=3,epsilon=.03,steps=7,step_size=.005,seed=2026,batch_size=8,learning_rate=1e-5),
              'epochs':[dict(epoch=i,validation_samples=689,mean_batch_loss=.2,validation_clean_accuracy=.7,validation_pgd_accuracy=i/10) for i in (1,2,3)],'best_epoch':3}
    write(t/'training.json',training)
    report=dict(status='COMPLETED',samples=781,independent_verification_approval=False,
                training_report_sha256=digest(t/'training.json'),test_manifest_sha256=digest(root/'configs/test_manifest.json'),
                epsilon=.03,steps=7,step_size=.005,restarts=1,seed=2026,batch_size=8,models={})
    for kind in ('original','trained'):
        with (e/(kind+'.csv')).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['relative_path','true_index','clean_pred','pgd_pred','linf'])
            for i in range(781):w.writerow([f'c/{i}.png',0,0,1,.03])
        report['models'][kind]=dict(sha256='a'*64 if kind=='original' else digest(t/'best.keras'),samples=781,
                                   clean_correct=781,pgd_correct=0,clean_accuracy=1.,pgd_accuracy=0.,attack_success_rate=1.,csv_sha256=digest(e/(kind+'.csv')))
    write(e/'evaluation.json',report)
    return root,t,e


def test_valid_saved_evidence(evidence):
    root,t,e=evidence
    assert audit_mobile(t,e,root)['epochs']==3


@pytest.mark.parametrize('mutation',['epoch','weights','asr','coverage','bound','split'])
def test_reject_corrupt_evidence(evidence,mutation):
    root,t,e=evidence
    if mutation=='weights':(t/'best.keras').write_bytes(b'changed')
    elif mutation=='epoch':
        v=json.loads((t/'training.json').read_text());v['epochs'].pop();write(t/'training.json',v)
    elif mutation=='asr':
        v=json.loads((e/'evaluation.json').read_text());v['models']['trained']['attack_success_rate']=.5;write(e/'evaluation.json',v)
    elif mutation=='split':
        v=json.loads((t/'split-audit.json').read_text());v['splits']['train'][0]['sha256']=v['splits']['test'][0]['sha256'];write(t/'split-audit.json',v)
        v=json.loads((t/'training.json').read_text());v['split_audit_sha256']=digest(t/'split-audit.json');write(t/'training.json',v)
    else:
        path=e/'trained.csv';lines=path.read_text().splitlines()
        if mutation=='coverage':lines[-1]=lines[-2]
        else:lines[-1]=lines[-1].replace('0.03','0.04')
        path.write_text('\n'.join(lines)+'\n')
        v=json.loads((e/'evaluation.json').read_text());v['models']['trained']['csv_sha256']=digest(path);write(e/'evaluation.json',v)
    with pytest.raises(ValueError):audit_mobile(t,e,root)


def test_missing_stages_cannot_pass(tmp_path):
    with pytest.raises((FileNotFoundError,ValueError)):
        audit_all(*([tmp_path]*5))
