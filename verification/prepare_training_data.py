"""Prepare a separate complete training copy, removing exact duplicates/leakage."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from verification.local_split_audit import audit_splits as inspect_splits
from adversarial_ai.training.adversarial_training import audit_splits as training_gate


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_downloads(inventory, staged, directory, expected_count):
    """Require one verified local record for every source ID, with no extras."""
    source_ids=[r['id'] for r in inventory];local_ids=[r['id'] for r in staged]
    if len(source_ids)!=expected_count or len(set(source_ids))!=expected_count:
        raise ValueError('source inventory incomplete or duplicated')
    if len(local_ids)!=expected_count or set(local_ids)!=set(source_ids):
        raise ValueError('download inventory incomplete or duplicated')
    paths=[r['path'] for r in staged]
    if len(set(paths))!=expected_count:raise ValueError('staged paths collide')
    root=Path(directory).resolve()
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual!=set(paths):raise ValueError('staged file inventory differs')
    for r in staged:
        p=root/r['path']
        if p.is_symlink() or not p.resolve().is_relative_to(root):raise ValueError('unsafe staged path')
        if p.stat().st_size!=r['bytes'] or digest(p)!=r['sha256']:
            raise ValueError('staged bytes differ')


def exclusion_plan(report):
    if report['decode_errors']:raise ValueError('image decoding failed')
    splits=report['splits'];train=splits['train']['files'];reasons=defaultdict(set)
    for key in ('sha256','pixel_sha256'):
        validation={r[key] for r in splits['valid']['files']}
        test={r[key] for r in splits['test']['files']}
        if len(validation)!=len(splits['valid']['files']):raise ValueError('validation duplicates require review')
        if validation&test:raise ValueError('validation/test overlap requires review')
        groups=defaultdict(list)
        for row in train:groups[row[key]].append(row['path'])
        for value,paths in groups.items():
            if value in validation or value in test:
                for path in paths:reasons[path].add('held_out_exact_overlap')
            if len({Path(path).parts[0] for path in paths})>1:
                for path in paths:reasons[path].add('conflicting_training_labels')
    # RGB identity covers differently encoded exact copies; all conflicting
    # labels and held-out copies were excluded before choosing a representative.
    groups=defaultdict(list)
    for row in train:
        if row['path'] not in reasons:groups[row['pixel_sha256']].append(row['path'])
    for paths in groups.values():
        for path in sorted(paths)[1:]:reasons[path].add('within_train_exact_duplicate')
    retained=sorted(r['path'] for r in train if r['path'] not in reasons)
    excluded=[{'path':path,'reasons':sorted(values)} for path,values in sorted(reasons.items())]
    return retained,excluded


def prepare(inventory_path,staged_path,train,valid,test,destination,repo_root,expected_count=8067):
    inventory=json.loads(Path(inventory_path).read_text());staged=json.loads(Path(staged_path).read_text())
    verify_downloads(inventory,staged,train,expected_count)
    report=inspect_splits({'train':train,'valid':valid,'test':test})
    retained,excluded=exclusion_plan(report)
    root=Path(repo_root);classes=json.loads((root/'configs/classes.json').read_text())
    names=[classes[str(i)] for i in range(len(classes))]
    if set(Path(p).parts[0] for p in retained)!=set(names):raise ValueError('a training class is empty or unexpected')
    destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.training-stage-',dir=destination.parent) as temporary:
        stage=Path(temporary);images=stage/'images';images.mkdir()
        for relative in retained:
            target=images/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(Path(train)/relative,target)
        gate=training_gate(images,valid,test,root/'configs/test_manifest.json',names)
        result={'status':'PREPARED_EXACT_AUDIT_ONLY','source_count':expected_count,
                'retained_count':len(retained),'excluded_count':len(excluded),
                'retained_class_counts':dict(sorted(Counter(Path(p).parts[0] for p in retained).items())),
                'inventory_sha256':digest(inventory_path),'staged_manifest_sha256':digest(staged_path),
                'near_duplicate_checked':False,'excluded':excluded,
                'note':'Originals and fixed held-out splits were not modified. Related frames may remain.'}
        (stage/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
        (stage/'split-audit.json').write_text(json.dumps(gate,indent=2)+'\n')
        # Publish only after all source completeness, hashes and training gates pass.
        stage.rename(destination)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inventory','staged','train','valid','test','destination'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--expected-count',type=int,default=8067)
    parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
    a=parser.parse_args()
    result=prepare(a.inventory,a.staged,a.train,a.valid,a.test,a.destination,a.repo_root,a.expected_count)
    print(json.dumps({k:v for k,v in result.items() if k!='excluded'},indent=2))


if __name__=='__main__':main()
