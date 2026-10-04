"""Create private recovery archives of changing experiment outputs.

Only explicitly listed result directories are included, never datasets. Uploads
use a caller-provided current Library helper. An uncertain/failed upload stops
the backup worker instead of creating duplicate retries. This worker itself is
not guaranteed to survive termination of the execution environment.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PATHS=[
 'results/extensions/iterative/bim-complete-20261004',
 'results/extensions/iterative/pgd-complete-20261004',
 'results/extensions/jsma/cnn-full-20261004',
 'results/extensions/queues/remaining-20261004',
 'results/extensions/adversarial_training/mobilenet-pgd7-20261004-serial',
 'results/extensions/mobilenet_adversarial_20261004',
]

def snapshot(destination,previous=None):
    files={}
    for relative in PATHS:
        folder=ROOT/relative
        if not folder.exists():continue
        for path in sorted(folder.rglob('*')):
            if path.is_symlink():raise ValueError('symlink in results')
            if not path.is_file() or path.suffix not in ('.json','.csv','.keras','.jsonl'):continue
            before=path.stat();data=path.read_bytes();after=path.stat()
            if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):return None,previous
            files[str(path.relative_to(ROOT))]=data
    digest=hashlib.sha256()
    for name,data in sorted(files.items()):digest.update(name.encode()+b'\0'+hashlib.sha256(data).digest())
    identity=digest.hexdigest()
    if not files or identity==previous:return None,previous
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination.mkdir(parents=True,exist_ok=True)
    archive=destination/f'AdversarialAI_remaining_checkpoint_{stamp}.zip'
    metadata={'created_at':stamp,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      'status':'RECOVERY_SNAPSHOT_NOT_COMPLETION_OR_APPROVAL','files':{n:hashlib.sha256(d).hexdigest() for n,d in files.items()}}
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        z.writestr('RECOVERY.json',json.dumps(metadata,indent=2)+'\n')
        for name,data in files.items():z.writestr(name,data)
    return archive,identity

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--upload-helper',type=Path,required=True)
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--interval',type=int,default=900)
    p.add_argument('--once',action='store_true')
    args=p.parse_args()
    if args.interval<60:raise ValueError('interval must be >=60 seconds')
    previous=None
    while True:
        archive,identity=snapshot(args.destination,previous)
        if archive:
            request={'uploads':[{'local_path':str(archive.resolve()),'purpose':'create_library_file','library_artifact_type':'other'}]}
            result=subprocess.run([sys.executable,str(args.upload_helper)],input=json.dumps(request),text=True,capture_output=True)
            receipt=archive.with_suffix('.receipt.json');receipt.write_text(result.stdout)
            if result.returncode:raise RuntimeError('backup upload failed or outcome uncertain; inspect private receipt')
            payload=json.loads(result.stdout)
            # Preserve the exact receipt. The helper exits nonzero on failed writes.
            if payload.get('isError') or payload.get('error'):raise RuntimeError('backup reported an error')
            previous=identity
            print(json.dumps({'archive':archive.name,'receipt':str(receipt),'upload_helper_exit_code':0}),flush=True)
        if args.once:return
        time.sleep(args.interval)

if __name__=='__main__':main()
