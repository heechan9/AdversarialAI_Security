"""Evidence-linked discrepancy history; never changes an experiment verdict."""
import argparse
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import re
try:
    from .status_registry import read_json, read_evidence, require
except ImportError:
    from status_registry import read_json, read_evidence, require

LOG='results/verification/discrepancy_log.json'
SCOPE={'models':['cnn','mobilenet'],'samples':781,'epsilons':[0,0.01,0.03,0.05],
       'methods':['gaussian','mean'],'pipelines':['clean','defended_clean','attacked','transfer_defended','adaptive_defended']}
TRANSITIONS={'open':{'observation':'open','action_recorded':'awaiting_retest'},
             'awaiting_retest':{'observation':'awaiting_retest','retest_fail':'open','retest_pass':'closed'},
             'closed':{'reopen':'open'}}
LABELS={'open':'미해결','awaiting_retest':'조치 기록 · 재검사 대기','closed':'재검사 근거 확인 · 종료'}


def stamp(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    require(dt.utcoffset() is not None,'timezone required')
    return dt


def nonempty(value):
    require(isinstance(value,str) and 0<len(value.strip())<=2000,'nonempty bounded text required')


def retest(root,event,issue):
    require(len(event['evidence'])==1,'one retest report required')
    report=read_evidence(root,event['evidence'][0])
    require(report.get('kind')=='cross_environment_retest','local or unrelated evidence cannot close discrepancy')
    require(report.get('issue_id')==issue['id'],'wrong issue evidence')
    require(report.get('source_commit')==event['source_commit'],'retest commit mismatch')
    require(report.get('scope')==issue['scope'],'retest scope differs')
    require(report.get('model_sha256')==issue['model_sha256'] and report.get('manifest_sha256')==issue['manifest_sha256'],'retest asset identity differs')
    require(report.get('operator_role')=='external_operator' and report.get('independent_operator') is True,'external operator evidence required')
    require(report.get('comparison')=={'label_match_fraction':1.0,'metric_abs_tolerance':1e-6,'linf_tolerance':1e-6},'retest criteria changed')
    require(report.get('completed') is True,'incomplete retest')
    result=report.get('result')
    require(result in ('PASS','FAIL'),'invalid retest result')
    count=report.get('difference_count')
    require(type(count) is int and count>=0,'invalid difference count')
    require((result=='PASS')==(count==0),'retest result contradicts differences')
    require(event['action']==('retest_pass' if result=='PASS' else 'retest_fail'),'event contradicts retest')


def validate_issue(root,issue):
    require(issue['id']=='cross-environment-01','unknown issue')
    nonempty(issue['title'])
    require(issue['scope']==SCOPE,'issue scope changed')
    require(set(issue['model_sha256'])=={'cnn','mobilenet'},'missing models')
    require(all(re.fullmatch('[0-9a-f]{64}',s) for s in [*issue['model_sha256'].values(),issue['manifest_sha256']]),'invalid asset hash')
    # Asset identity must remain linked to the actual experiment, not a replacement dataset.
    contract=read_json((root/'configs/stage_b_verification_contract.json').read_bytes())
    models={('cnn' if m['id']=='cnn_baseline' else m['id']):m['sha256'] for m in contract['models']}
    require(issue['model_sha256']==models,'model identity differs from contract')
    registry=read_json((root/'configs/test_manifest.json').read_bytes())
    require(registry['test_samples']==781,'manifest scope')
    import hashlib
    require(hashlib.sha256((root/'configs/test_manifest.json').read_bytes()).hexdigest()==issue['manifest_sha256'],'manifest hash differs')
    history=issue['history'];require(isinstance(history,list) and 1<=len(history)<=100,'history required')
    state=None;previous=None
    for index,event in enumerate(history):
        nonempty(event['note']);nonempty(event['actor_role'])
        require(re.fullmatch('[0-9a-f]{40}',event['source_commit']) is not None,'invalid source commit')
        at=stamp(event['at']);require(previous is None or at>=previous,'history out of order');previous=at
        require(type(event['seq']) is int and event['seq']==index,'history sequence mismatch')
        require(event['evidence'] and len({e['path'] for e in event['evidence']})==len(event['evidence']),'evidence required')
        for entry in event['evidence']:read_evidence(root,entry)
        if index==0:
            require(event['action']=='registered','registration must be first');state='open'
        else:
            action=event['action'];require(action in TRANSITIONS[state],'invalid state transition')
            if action in ('retest_pass','retest_fail'):retest(root,event,issue)
            state=TRANSITIONS[state][action]
    require(issue['state']==state,'declared state contradicts history')
    return {'id':issue['id'],'title':issue['title'],'state':state,'label':LABELS[state],
            'last_note':history[-1]['note'],'event_count':len(history),
            'events':[{'action':e['action'],'at':e['at'],'note':e['note']} for e in history]}


def transition(root,issue,event):
    """Return a new record; never mutate or erase the previous history."""
    validate_issue(root,issue)
    result=deepcopy(issue);event=deepcopy(event)
    require(event['action'] in TRANSITIONS[result['state']],'invalid state transition')
    event['seq']=len(result['history']);result['history'].append(event)
    result['state']=TRANSITIONS[result['state']][event['action']]
    validate_issue(root,result)
    return result


def build(root):
    root=Path(root).resolve();data=read_json((root/LOG).read_bytes())
    require(data['schema_version']==1 and len(data['issues'])==1,'issue log coverage')
    return [validate_issue(root,issue) for issue in data['issues']]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    print(json.dumps(build(args.repo_root),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
