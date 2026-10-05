"""Generate the reviewed recovery notebook from existing setup cells."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def main():
    original = json.loads((ROOT/'notebooks/AdversarialAI_Full_Extensions_GPU.ipynb').read_text())
    cells = []
    def add(kind, text):
        cell = dict(cell_type=kind, metadata={}, source=text.splitlines(keepends=True))
        if kind == 'code':
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    add('markdown', '# GPU 중단 복구 — 남은 조건 실행\n'
        'GPU 할당 후 아래 셀을 순서대로 실행합니다. 기존 전체 실행 셀을 실행하지 않습니다. '
        'BIM/PGD 부모 결과를 검사하고 PGD 11조건을 상속합니다. 환경 불일치 시 중단합니다. '
        '이 노트북은 첫 복구 시도용입니다. 재중단되면 저장 산출물을 다시 감사해야 하며 전체 재실행하지 마세요. '
        'Drive 백업에는 비공개 가중치가 포함됩니다. 폴더를 공개하지 마세요.\n')
    setup = ''.join(original['cells'][1]['source'])
    setup = setup.replace("COMMIT='e974c4bb21ac2041dfbb93fdb18c1983dd6e402e'",
        "import re\nCOMMIT=input('Reviewed execution SHA (40 hex): ').strip()\n"
        "if not re.fullmatch(r'[0-9a-f]{40}',COMMIT): raise ValueError('Explicit reviewed SHA required')\n"
        "print('Pinned recovery source:',COMMIT)")
    add('code', setup)
    add('code', ''.join(original['cells'][2]['source']).replace('다음 셀은 전체 5단계를 순차 실행합니다.', '다음 셀은 부모 결과를 감사합니다.'))
    add('code', '''os.chdir(REPO)
sys.path.insert(0,str(REPO));sys.path.insert(0,str(REPO/'src'))
from verification.iterative_result_audit import audit
PARENT=DEST/'full-gpu-20261004T120332'
def locate(name):
    candidates=list(PARENT.rglob(name+'/run.json'))
    assert len(candidates)==1, ('부모 결과 경로를 유일하게 찾을 수 없음',name)
    return candidates[0].parent
BIM=locate('full-gpu-20261004T120332-bim')
PGD_PARENT=locate('full-gpu-20261004T120332-pgd')
assert audit(BIM,REPO)['result']=='FULL_OUTPUTS_CONSISTENT'
assert audit(PGD_PARENT,REPO)['checked_conditions']==11
RUN='recovery-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
PRIVATE=DEST/RUN
PRIVATE.mkdir(exist_ok=False)
(PRIVATE/'execution-source.json').write_text(json.dumps({'source_commit':COMMIT},indent=2))
PGD=REPO/'results/extensions/iterative'/(RUN+'-pgd')
JSMA=REPO/'results/extensions/jsma'/(RUN+'-jsma')
TRAIN=REPO/'results/extensions/adversarial_training'/(RUN+'-train')
EVAL=REPO/'results/extensions'/(RUN+'-eval')
def stage(name,out,args):
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==COMMIT, 'Execution source changed'
    run_logged([PY,'-m','verification.recovery_stage','--output',str(out),'--backup',str(PRIVATE/name),'--',*args],env=ENV)
print('부모 감사 완료; 복구 ID:',RUN)
''')
    add('code', '''stage('pgd',PGD,['-m','adversarial_ai.evaluation.iterative_evaluation','--attack','pgd','--steps','20','--step-size','.005','--restarts','5','--seed','2026','--batch-size','16','--run-id',PGD.name,'--data-dir',str(WORK/'data/test'),'--resume-from',str(PGD_PARENT)])
assert audit(PGD,REPO)['result']=='FULL_OUTPUTS_CONSISTENT'
''')
    add('code', '''stage('jsma',JSMA,['-m','adversarial_ai.evaluation.jsma_evaluation','--model','cnn','--defense','none','--theta','1','--gamma','.01','--max-steps','246','--limit','781','--run-id',JSMA.name,'--data-dir',str(WORK/'data/test')])
from verification.jsma_saved_audit import audit as audit_jsma
assert audit_jsma(JSMA,REPO)['result']=='FULL_SAVED_EVIDENCE_CONSISTENT'
''')
    add('code', '''stage('training',TRAIN,['-m','adversarial_ai.training.adversarial_training','--model','mobilenet','--train-dir',str(WORK/'data/train-prepared/images'),'--validation-dir',str(WORK/'data/valid'),'--test-dir',str(WORK/'data/test'),'--epochs','3','--epsilon','.03','--steps','7','--step-size','.005','--seed','2026','--batch-size','8','--learning-rate','.00001','--run-id',TRAIN.name])
''')
    add('code', '''stage('evaluation',EVAL,['verification/mobilenet_pgd7_test_evaluation.py','--trained-dir',str(TRAIN),'--test-dir',str(WORK/'data/test'),'--output-dir',str(EVAL)])
from verification.full_extension_audit import audit_all
result=audit_all(BIM,PGD,JSMA,TRAIN,EVAL,REPO)
(PRIVATE/'saved-evidence-audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
print('저장 증거 감사 완료. GPU 로그·lineage·공개 범위·CI 검토 및 최종 병합은 별도입니다.')
''')
    notebook=dict(nbformat=4,nbformat_minor=5,metadata=original['metadata'],cells=cells)
    for i,cell in enumerate(cells):cell['id']='recovery-'+str(i)
    (ROOT/'notebooks/AdversarialAI_Recovery_GPU.ipynb').write_text(json.dumps(notebook,ensure_ascii=False,indent=1)+'\n')


if __name__ == '__main__':main()
