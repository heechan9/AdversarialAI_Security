"""Controlled oneDNN on/off full-evaluator runs, separate from Stage B approval."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE = '491b973cd9f4840664044a83c0d62d1ee1bb98e8'


def run(repo, output):
    repo, output = repo.resolve(), output.resolve()
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repo, text=True)
    if sha != BASE or dirty:
        raise ValueError('Use an unchanged checkout at '+BASE)
    if output.is_relative_to(repo) or repo.is_relative_to(output):
        raise ValueError('Output must be outside checkout')
    output.mkdir(parents=True, exist_ok=False)
    report = {'kind': 'onednn_controlled_diagnostic', 'stage_b_approved': False,
              'source_commit': sha, 'started_utc': datetime.now(timezone.utc).isoformat(), 'runs': []}
    env = dict(os.environ, PYTHONPATH=str(repo/'src'), PYTHONUNBUFFERED='1')
    report['controlled_environment'] = {k: env.get(k) for k in ('TF_DETERMINISTIC_OPS', 'TF_NUM_INTRAOP_THREADS', 'TF_NUM_INTEROP_THREADS', 'OMP_NUM_THREADS', 'CUDA_VISIBLE_DEVICES')}
    report['python'] = sys.version
    (output/'environment.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True),encoding='utf-8')
    try:
        for value in ('1', '0'):
            for method, module in [('gaussian','defense_evaluation'), ('mean','mean_defense_evaluation')]:
                name = f'onednn-{value}-{method}'
                command = [sys.executable,'-m','adversarial_ai.evaluation.'+module,'--output',str(output/name)]
                print('Running '+name, flush=True)
                with (output/(name+'.log')).open('x',encoding='utf-8') as log:
                    result = subprocess.run(command,cwd=repo,env=dict(env,TF_ENABLE_ONEDNN_OPTS=value),stdout=log,stderr=subprocess.STDOUT)
                report['runs'].append({'name':name,'TF_ENABLE_ONEDNN_OPTS':value,'command':command,'returncode':result.returncode})
                if result.returncode:
                    raise RuntimeError('Evaluator failed: '+name)
        report['execution_status'] = 'COMPLETED_NOT_COMPARED'
    except BaseException:
        report['execution_status'] = 'INCOMPLETE'
        raise
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        with (output/'diagnostic-report.json').open('x',encoding='utf-8') as f:
            json.dump(report,f,ensure_ascii=False,indent=2)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.repo_root,args.output)
