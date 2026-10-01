"""Collect a candidate original environment and trace without modifying its packages."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

BASE = '491b973cd9f4840664044a83c0d62d1ee1bb98e8'
EXPECTED = {'python':'3.11.15', 'tensorflow':'2.21.0', 'keras':'3.15.1'}
MODEL_HASHES = {
    'cnn_baseline.h5':'cb256b1a5d6f605d355334e4e8667257a2bfbd29e08836cc4114869bd7068701',
    'mobilenet_finetuned.h5':'58c4878fa1480035d0bd5a63f8c3e22beac3a03f27f1aada6690b27f167129ae',
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def package_evidence(evidence, archive):
    if archive.exists():
        raise FileExistsError(archive)
    fd,name=tempfile.mkstemp(prefix='evidence-',suffix='.partial',dir=archive.parent)
    os.close(fd)
    temporary=Path(name)
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(evidence.rglob('*')):
                if p.is_file():z.write(p,p.relative_to(evidence).as_posix())
        with zipfile.ZipFile(temporary) as z:
            if z.testzip() is not None:raise ValueError('ZIP CRC verification failed')
        temporary.replace(archive)
    finally:
        temporary.unlink(missing_ok=True)


def inventory():
    packages = sorted([{'name':d.metadata.get('Name','unknown'), 'version':d.version}
                       for d in importlib.metadata.distributions()],key=lambda d:d['name'].lower())
    versions = {d['name'].lower():d['version'] for d in packages}
    cpu = {'processor':platform.processor(), 'logical_count':os.cpu_count()}
    if platform.system()=='Windows':
        try:
            result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
                'Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json -Compress'],
                capture_output=True,text=True,timeout=20,check=True)
            cpu['windows_processor']=json.loads(result.stdout)
        except (OSError,subprocess.SubprocessError,ValueError) as error:
            cpu['detail_unavailable']=type(error).__name__
    return dict(python=platform.python_version(),platform=platform.platform(),system=platform.system(),
                executable=sys.executable,cpu=cpu,packages=packages,
                tensorflow=versions.get('tensorflow'),keras=versions.get('keras'),
                environment={k:os.environ.get(k) for k in ['CONDA_DEFAULT_ENV','CONDA_PREFIX','TF_ENABLE_ONEDNN_OPTS',
                'TF_NUM_INTRAOP_THREADS','TF_NUM_INTEROP_THREADS','OMP_NUM_THREADS','TF_DETERMINISTIC_OPS',
                'CUDA_VISIBLE_DEVICES','ONEDNN_MAX_CPU_ISA','DNNL_MAX_CPU_ISA']})


def matches_recorded(env):
    return env['system']=='Windows' and all(env.get(k)==v for k,v in EXPECTED.items())


def manifest_rows(manifest):
    rows=manifest['test_files']
    names=[r['relative_path'] for r in rows]
    if manifest.get('test_samples')!=781 or len(names)!=781 or len(set(names))!=781:
        raise ValueError('Expected 781 unique manifest entries')
    for name in names:
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
            raise ValueError('Invalid manifest path')
    return rows


def verify_and_copy(source_repo, models, data, target):
    subprocess.run(['git','clone','--shared','--no-checkout','--config','core.autocrlf=false',str(source_repo),str(target)],check=True,
                   stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    subprocess.run(['git','-C',str(target),'checkout','--detach',BASE],check=True,
                   stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    manifest=json.loads((target/'configs/test_manifest.json').read_text(encoding='utf-8-sig'))
    rows=manifest_rows(manifest)
    actual={p.relative_to(data).as_posix() for p in data.rglob('*') if p.is_file()}
    if actual!={r['relative_path'] for r in rows}:
        raise ValueError('Dataset paths differ from exact 781-file manifest')
    pairs=[(models/n,target/'models'/n,h) for n,h in MODEL_HASHES.items()]
    pairs += [(data/r['relative_path'],target/'data/test'/r['relative_path'],r['sha256']) for r in rows]
    for original,dest,expected in pairs:
        if not original.is_file() or sha(original)!=expected:
            raise ValueError('Input hash mismatch: '+str(original))
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(original,dest)
        if sha(dest)!=expected:
            raise ValueError('Copied input hash mismatch: '+str(dest))
    return dict(models_verified=2,images_verified=781)


def run(args):
    source,models,data=[p.resolve() for p in (args.source_repo,args.models_dir,args.data_dir)]
    output=args.output.resolve()
    for p in (source,models,data):
        if output.is_relative_to(p) or p.is_relative_to(output):
            raise ValueError('Output must not overlap source repo or input assets')
    output.mkdir(parents=True,exist_ok=False)
    evidence=output/'evidence';evidence.mkdir()
    env=inventory()
    (evidence/'environment.json').write_text(json.dumps(env,indent=2)+'\n',encoding='utf-8')
    report=dict(kind='candidate_original_environment_trace',stage_b_approved=False,
        source_commit=BASE,started_utc=datetime.now(timezone.utc).isoformat(),inference_performed=False,
        recorded_version_match=matches_recorded(env),original_environment_identity_proven=False,
        note='Matching versions are necessary for the default gate, not proof this is the historical environment.')
    try:
        if args.require_recorded_environment and not report['recorded_version_match']:
            raise ValueError('Use original Windows Python 3.11.15 / TensorFlow 2.21.0 / Keras 3.15.1 environment; no packages were changed')
        tool_dir=Path(__file__).resolve().parent
        selection=tool_dir.parent/'results/verification/stage_b/hyeonsu_01_review/local_followup.json'
        for p in (Path(__file__).resolve(),tool_dir/'stage_b_trace.py',selection):
            shutil.copyfile(p,evidence/p.name)
        report['input_verification']=verify_and_copy(source,models,data,output/'source')
        if args.execute:
            command=[sys.executable,str(evidence/'stage_b_trace.py'),'--repo-root',str(output/'source'),
                     '--selection',str(evidence/selection.name),'--output',str(evidence/'native-trace'),'--native-settings']
            report['command']=command
            child_env=dict(os.environ,PYTHONUNBUFFERED='1',PYTHONUTF8='1')
            print('Tracing five remaining predictions with inherited numerical settings...',flush=True)
            report['inference_attempted']=True
            report['inference_performed']=None
            report['status']='TRACE_RUNNING_NOT_COMPLETE'
            (evidence/'run-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            with (evidence/'native-trace.log').open('x',encoding='utf-8') as log:
                completed=subprocess.run(command,env=child_env,stdout=log,stderr=subprocess.STDOUT)
            report['returncode']=completed.returncode
            if completed.returncode:
                raise RuntimeError('Trace failed; preserve the evidence ZIP and log')
            trace=json.loads((evidence/'native-trace/report.json').read_text())
            if trace['execution_status']!='COMPLETE' or not trace['weights_unchanged'] or len(trace['results'])!=5:
                raise ValueError('Incomplete or mutated trace')
            report['inference_performed']=True
            report['predictions']=[dict(key=r['key'],reference=r['selected'][0]['reference'],
                submitted=r['selected'][0]['actual'],observed=r['native'][0]['prediction']) for r in trace['results']]
            report['status']='TRACE_COMPLETE_NOT_APPROVED'
        else:
            report['status']='PREPARED_NOT_EXECUTED'
    except BaseException as error:
        report['status']='INCOMPLETE'
        report['error']=str(error)
        raise
    finally:
        report['finished_utc']=datetime.now(timezone.utc).isoformat()
        (evidence/'run-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        files=sorted(p for p in evidence.rglob('*') if p.is_file())
        checks={p.relative_to(evidence).as_posix():sha(p) for p in files}
        (evidence/'SHA256.json').write_text(json.dumps(checks,indent=2)+'\n')
        archive=output/'return-evidence.zip'
        package_evidence(evidence,archive)
        print('Return file: '+str(archive),flush=True)
        print('Status: '+report['status'],flush=True)


if __name__=='__main__':
    home=Path.home();repo=home/'AdversarialAI_Security'
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-repo',type=Path,default=repo)
    p.add_argument('--models-dir',type=Path,default=repo/'models')
    p.add_argument('--data-dir',type=Path,default=home/'adversarial-fgsm-candidate-01/checkout/data/test')
    p.add_argument('--output',type=Path,default=home/('AdversarialAI_original_trace_'+datetime.now().strftime('%Y%m%d_%H%M%S')))
    p.add_argument('--execute',action='store_true')
    p.add_argument('--require-recorded-environment',action='store_true')
    run(p.parse_args())
