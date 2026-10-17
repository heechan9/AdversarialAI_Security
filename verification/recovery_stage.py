"""Run one GPU stage with private periodic backups; never auto-retry a stage."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def backup(source, destination):
    if not source.exists():
        return
    for path in source.rglob('*'):
        if path.is_symlink():
            raise ValueError('result symlink forbidden')
        if not path.is_file() or path.suffix not in ('.json', '.jsonl', '.csv', '.keras', '.log'):
            continue
        before = path.stat()
        target = destination/path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(target.name+'.copying')
        import shutil
        shutil.copyfile(path, temp)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns):
            temp.replace(target)
        else:
            temp.unlink()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--backup', type=Path, required=True)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not command:
        p.error('missing stage command')
    if a.output.exists() or a.backup.exists():
        raise ValueError('existing stage output: inspect saved evidence before any retry')
    a.backup.mkdir(parents=True)
    probe = subprocess.check_output([sys.executable, '-c',
        "import tensorflow as tf,json; g=tf.config.list_physical_devices('GPU'); assert g; print(json.dumps([str(x) for x in g]))"], text=True)
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    state = dict(status='RUNNING', source_commit=source, gpu_probe=probe.strip(),
                 command=command, started_at=time.time(), independent_verification_approval=False)
    def save():
        state['observed_at'] = time.time()
        temp = a.backup/'stage.json.tmp'
        temp.write_text(json.dumps(state, indent=2)+'\n')
        temp.replace(a.backup/'stage.json')
    save()
    with (a.backup/'stage.log').open('x') as log:
        process = subprocess.Popen([sys.executable, '-u', *command], stdout=log, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                backup(a.output, a.backup/'outputs')
                save()
                try:
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
            backup(a.output, a.backup/'outputs')
            state['exit_code'] = process.returncode
            state['status'] = 'EXITED_ZERO_REQUIRES_AUDIT' if process.returncode == 0 else 'ERROR'
            save()
            if process.returncode:
                raise RuntimeError('stage failed; inspect private stage.log')
        except BaseException:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            state['status'] = 'INTERRUPTED_OR_ERROR'
            save()
            raise


if __name__ == '__main__':
    main()
