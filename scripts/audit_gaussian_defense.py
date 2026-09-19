"""Read-only independent audit of the archived experimental defense run.

Standard library only. Never imports or executes the evaluator or model code.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import zipfile


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def document(data):
    return json.loads(data, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rows(data, expected_fields=None, max_rows=None):
    reader = csv.reader(io.StringIO(data.decode('utf-8-sig')))
    fields = next(reader, None)
    require(fields and len(set(fields)) == len(fields), 'CSV header')
    if expected_fields is not None:
        require(fields == expected_fields, 'exact CSV schema')
    values = []
    for row in reader:
        if not row:  # Preserve DictReader's handling of blank lines.
            continue
        require(len(row) == len(fields), 'CSV width')
        require(max_rows is None or len(values) < max_rows, 'CSV row count')
        values.append(dict(zip(fields, row)))
    return values


KEYS = ('clean', 'defended_clean', 'attacked', 'transfer_defended', 'adaptive_defended')


def aggregate(data):
    true = [int(row['true_index']) for row in data]
    predicted = {key: [int(row[key+'_pred']) for row in data] for key in KEYS}
    base = [a == b for a,b in zip(true,predicted['clean'])]
    defended = [a == b for a,b in zip(true,predicted['defended_clean'])]
    common = [a and b for a,b in zip(base,defended)]
    def rate(mask, key):
        den = sum(mask)
        num = sum(m and a != b for m,a,b in zip(mask,true,predicted[key]))
        return dict(successes=num, denominator=den, asr=num/den if den else None)
    return dict(samples=len(data), accuracy={key: sum(a==b for a,b in zip(true,p))/len(data) if data else None
                    for key,p in predicted.items()},
        clean_harmed=sum(a and not b for a,b in zip(base,defended)),
        clean_recovered=sum(b and not a for a,b in zip(base,defended)),
        asr_original=rate(base,'attacked'), asr_transfer_defended=rate(defended,'transfer_defended'),
        asr_adaptive_defended=rate(defended,'adaptive_defended'),
        common_clean_correct={key:rate(common,key) for key in KEYS[2:]})


SOURCE_PATHS = frozenset({
    'src/adversarial_ai/evaluation/defense_evaluation.py',
    'src/adversarial_ai/defenses/gaussian.py',
    'src/adversarial_ai/attacks/fgsm.py',
})

# The archived run expands to about 0.53 MB in twelve CSV/JSON members.
# Leave room for legitimate repacks while bounding every supplier-owned read.
MAX_PROVENANCE_BYTES = 65_536
MAX_ARCHIVE_BYTES = 2_000_000
MAX_MEMBER_BYTES = 1_000_000
MAX_TOTAL_BYTES = 2_000_000
EXPECTED_MEMBERS = frozenset(
    {'summary.json', 'contract.json', 'SHA256.json', 'COMPLETE.json'} |
    {f'{model}_eps_{epsilon}_samples.csv'
     for model in ('cnn', 'mobilenet') for epsilon in ('0', '0.01', '0.03', '0.05')}
)


def bounded_read(stream, limit, label):
    data = stream.read(limit + 1)
    require(len(data) <= limit, 'size limit: ' + label)
    return data


def bounded_file(path, limit):
    with path.open('rb') as stream:
        return bounded_read(stream, limit, path.name)


def verify_sources(repo, source_files):
    """Bind this checkout to recorded execution sources, allowing only LF/CRLF.

    This is compatibility with archived source bytes, not Git ancestry proof.
    A changed implementation requires a separate historical checkout for audit.
    """
    require(isinstance(source_files, dict) and set(source_files) == SOURCE_PATHS,
            'source inventory')
    for name, expected in source_files.items():
        require(isinstance(expected, str) and len(expected) == 64 and
                all(c in '0123456789abcdef' for c in expected), 'source hash format')
        path = repo / name
        require(not any(part.is_symlink() for part in [path, *path.parents]),
                'symlink source')
        raw = path.read_bytes()
        lf = raw.replace(b'\r\n', b'\n')
        require(expected in {digest(raw), digest(lf), digest(lf.replace(b'\n', b'\r\n'))},
                'source file mismatch: ' + name)


def audit(repo, root):
    provenance = document(bounded_file(root/'PROVENANCE.json', MAX_PROVENANCE_BYTES))
    archive = bounded_file(root/'original_bundle.zip', MAX_ARCHIVE_BYTES)
    require(digest(archive) == provenance['original_bundle_sha256'], 'original ZIP hash')
    members = {}
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        infos = z.infolist()
        require(len(infos) == len(EXPECTED_MEMBERS), 'archive member count')
        require(sum(info.file_size for info in infos) <= MAX_TOTAL_BYTES, 'ZIP total size limit')
        names = set()
        checked = []
        # Validate the entire inventory before opening even the first member.
        for info in infos:
            path = PurePosixPath(info.filename.replace('\\','/'))
            require(not path.is_absolute() and '..' not in path.parts and len(path.parts)==2
                    and ':' not in info.filename and path.name not in names, 'unsafe/duplicate ZIP member')
            require(path.name in EXPECTED_MEMBERS, 'archive inventory')
            require(info.file_size <= MAX_MEMBER_BYTES, 'ZIP member size limit')
            require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'unsupported ZIP codec')
            require(not info.flag_bits & 1, 'encrypted ZIP member')
            names.add(path.name)
            checked.append((info, path.name))
        total = 0
        for info, name in checked:
            # Reading accepted members to EOF also verifies their CRC, without
            # the unbounded duplicate decompression previously done by testzip.
            with z.open(info) as stream:
                data = bounded_read(stream, min(MAX_MEMBER_BYTES, MAX_TOTAL_BYTES - total), name)
            require(len(data) == info.file_size, 'ZIP member size mismatch')
            total += len(data)
            members[name] = data
            local = root/name
            require(not local.is_symlink(), 'symlink evidence')
            require(bounded_file(local, MAX_MEMBER_BYTES) == data, 'archive member mismatch: '+name)
    checks = document(members['SHA256.json'])
    require(set(members) == set(checks) | {'SHA256.json','COMPLETE.json'}, 'archive inventory')
    for name, value in checks.items():
        require(digest(members[name]) == value, 'member checksum')
    complete = document(members['COMPLETE.json'])
    require(complete['status']=='experimental_completed' and complete['promoted'] is False
            and complete['weights_unchanged'] is True and complete['inputs_unchanged'] is True, 'completion status')
    for key,name in [('summary_sha256','summary.json'),('checksums_sha256','SHA256.json')]:
        require(complete[key]==digest(members[name]), 'completion hash')
    contract = document(members['contract.json'])
    require(contract['status']=='experimental' and contract['promoted'] is False, 'contract status')
    require(contract['source_sha']==provenance['source_commit'], 'source identity')
    verify_sources(repo, contract['source_files'])
    manifest = document((repo/'configs/test_manifest.json').read_bytes())
    classes = document((repo/'configs/classes.json').read_bytes())
    for name,value in contract['inputs_sha256'].items():
        if name.startswith('models/'):
            require(any(m['path']==name and m['sha256']==value for m in manifest['models']), 'model metadata hash')
        else:
            require(name in ('configs/test_manifest.json','configs/classes.json',
                'results/clean/cnn_baseline_eval.csv','results/clean/mobilenet_eval.csv'), 'input path')
            raw=(repo/name).read_bytes();lf=raw.replace(b'\r\n',b'\n')
            require(value in (digest(raw),digest(lf),digest(lf.replace(b'\n',b'\r\n'))), 'input hash')
    summary=document(members['summary.json'])
    seen=set();total=0
    expected_fields=['relative_path','epsilon','true_index']+[k+'_pred' for k in KEYS]+['original_linf','adaptive_linf']
    for model,clean_name in [('cnn','cnn_baseline_eval.csv'),('mobilenet','mobilenet_eval.csv')]:
        canonical=rows((repo/'results/clean'/clean_name).read_bytes());stable=None
        # Attack strengths come from existing canonical FGSM summary, not a new sweep.
        epsilons=[float(r['epsilon']) for r in rows((repo/f'results/attacks/provisional/fgsm_{model}.csv').read_bytes())]
        require(contract['epsilons']==epsilons, 'epsilon contract')
        for epsilon in epsilons:
            data=rows(members[f'{model}_eps_{epsilon:g}_samples.csv'],
                      expected_fields=expected_fields, max_rows=len(canonical))
            require(len(data)==len(canonical)==len(manifest['test_files']), 'row count')
            old=rows((repo/f'results/attacks/provisional/fgsm_{model}_eps_{epsilon:g}_samples.csv').read_bytes())
            require(len(old)==len(data), 'old row count')
            for row,clean,record,attack in zip(data,canonical,manifest['test_files'],old):
                require(list(row)==expected_fields, 'exact CSV schema')
                require(row['relative_path']==clean['relative_path']==record['relative_path'], 'sample path/order')
                require(int(row['true_index'])==int(clean['true_index']) and
                        int(row['clean_pred'])==int(clean['predicted_index']), 'canonical clean')
                require(int(row['attacked_pred'])==int(attack['adversarial_predicted_index']), 'canonical attack')
                require(float(row['epsilon'])==epsilon, 'row epsilon')
                for key in ['true_index']+[k+'_pred' for k in KEYS]:
                    require(row[key].isdigit() and 0<=int(row[key])<len(classes), 'prediction index')
                for key in ['original_linf','adaptive_linf']:
                    value=float(row[key]);require(math.isfinite(value) and 0<=value<=epsilon+1e-6,'Linf')
                if epsilon==0:
                    require(row['clean_pred']==row['attacked_pred'] and
                        row['defended_clean_pred']==row['transfer_defended_pred']==row['adaptive_defended_pred'] and
                        float(row['original_linf'])==float(row['adaptive_linf'])==0, 'epsilon zero')
            pair=[(row['clean_pred'],row['defended_clean_pred']) for row in data]
            require(stable is None or stable==pair, 'normal predictions changed');stable=pair
            match=[item for item in summary if item['model']==model and item['epsilon']==epsilon]
            require(len(match)==1,'summary duplicate/missing')
            item=match[0];require(item['overall']==aggregate(data),'aggregate mismatch')
            expected={label:aggregate([row for row in data if int(row['true_index'])==int(idx)]) for idx,label in classes.items()}
            require(item['classes']==expected,'class aggregate mismatch')
            seen.add((model,epsilon));total+=len(data)
    require(len(summary)==len(seen), 'extra summary')
    return dict(status='PASSED',rows=total,conditions=len(seen),class_summaries=len(seen)*len(classes),
                limits='No independent inference, raw-pixel checks or model-file hashing; PC record and artifact audit only')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--evidence',type=Path)
    args=parser.parse_args()
    try:
        print(json.dumps(audit(args.repo,args.evidence or args.repo/'results/defenses/experimental/gaussian_run_01'),indent=2))
    except (ValueError,KeyError,OSError,TypeError,zipfile.BadZipFile) as exc:
        parser.exit(1,f'GAUSSIAN EVIDENCE AUDIT FAILED: {exc}\n')
