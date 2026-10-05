"""Publish aggregate BIM metrics only, after raw CSV audit."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from verification.iterative_result_audit import audit
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run_dir',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    checked=audit(a.run_dir,ROOT)
    r=json.loads((a.run_dir/'run.json').read_text())
    if checked['result']!='FULL_OUTPUTS_CONSISTENT' or r['settings']['attack']!='bim':
        raise ValueError('completed audited BIM required')
    a.output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for c in r['conditions']:
        for pipeline,m in c['metrics'].items():
            rows.append(dict(model=c['model'],filter=c['method'],epsilon=c['epsilon'],pipeline=pipeline,
                samples=c['samples'],accuracy=m['accuracy'],asr=m['asr'],
                asr_successes=m['asr_successes'],asr_denominator=m['asr_denominator']))
    with (a.output/'metrics.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    evidence=dict(audit=checked,parent_report_sha256=hashlib.sha256((a.run_dir/'run.json').read_bytes()).hexdigest(),
        csv_hashes={c['csv']:c['sha256'] for c in r['conditions']},
        note='Aggregate results only; no private images or model weights. Independent approval not performed.')
    (a.output/'audit-summary.json').write_text(json.dumps(evidence,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,2,figsize=(10,7),sharex=True,sharey=True)
    for ax,(model,method) in zip(axes.flat,[(m,f) for m in ('cnn','mobilenet') for f in ('gaussian','mean')]):
        for pipe in ('clean','defended_clean','attacked','transfer_defended','adaptive_defended'):
            selected=sorted((v for v in rows if v['model']==model and v['filter']==method and v['pipeline']==pipe),key=lambda v:v['epsilon'])
            ax.plot([v['epsilon'] for v in selected],[v['accuracy'] for v in selected],marker='o',label=pipe)
        ax.set_title(model+' / '+method);ax.set_ylim(0,1);ax.grid(alpha=.2)
        ax.set_xlabel('epsilon');ax.set_ylabel('accuracy (781 samples)')
    handles,labels=axes.flat[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=3)
    fig.suptitle('BIM: 10 steps, step size 0.005, one restart')
    fig.tight_layout(rect=(0,.1,1,.96));fig.savefig(a.output/'accuracy.svg');plt.close(fig)
    lines=['# BIM GPU 저장 결과 요약','',
        '실행 `full-gpu-20261004T120332`의 BIM 16조건을 원시 CSV와 대조해 검산했다. 각 조건은 같은 테스트 781장을 사용한다. 외부 독립검증 승인은 수행하지 않았다.','',
        '![BIM accuracy](accuracy.svg)','',
        '| 모델 | 필터 | ε | 공격 정확도 | 전달 방어 정확도 | 방어 인지 정확도 |',
        '|---|---|---:|---:|---:|---:|']
    for c in r['conditions']:
        m=c['metrics'];lines.append(f"| {c['model']} | {c['method']} | {c['epsilon']} | {m['attacked']['accuracy']:.4f} | {m['transfer_defended']['accuracy']:.4f} | {m['adaptive_defended']['accuracy']:.4f} |")
    lines+=['','전달 방어는 원본 모델을 공격한 뒤 필터를 적용하고, 방어 인지 공격은 필터를 포함한 모델을 공격한다. 두 결과를 같은 방어 성능으로 해석하지 않는다. ε=0은 대조군이다. ASR의 분모는 해당 기준 파이프라인에서 정답인 표본 수이며 `metrics.csv`에 함께 기록했다.',
        '', '이 표는 BIM 설정에 한정된다. PGD·JSMA·적대적 학습의 완료나 일반적인 강건성을 증명하지 않는다. 확률 배열 비교와 실제 선박 환경 검증도 포함하지 않는다.','']
    (a.output/'README.md').write_text('\n'.join(lines))


if __name__=='__main__':main()
