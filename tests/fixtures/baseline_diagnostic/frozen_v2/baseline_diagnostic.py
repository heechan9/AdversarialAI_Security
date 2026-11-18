"""Private diagnostic only. No inference, report mutation or approval."""
import csv
import hashlib
import types
import io
import json
import os
import re
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent
AUDITOR_SHA256 = 'edad00c391a69cd40bfee103ecd07088a178fe33488e34ec37169720b3a73dad'
audit_path = ROOT/'verification/iterative_result_audit.py'
audit_bytes = audit_path.read_bytes()
if hashlib.sha256(audit_bytes).hexdigest() != AUDITOR_SHA256:
    raise ValueError('pinned auditor hash mismatch')
# Execute the bytes just verified, rather than reopening a mutable source path.
audit_module = types.ModuleType('pinned_audit')
audit_module.__file__ = str(audit_path)
exec(compile(audit_bytes, str(audit_path), 'exec'), audit_module.__dict__)


def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_leaf(directory_fd, name):
    if not isinstance(name, str) or Path(name).name != name or name in ('.', '..'):
        raise ValueError('unsafe snapshot name')
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
    try:
        import stat
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('snapshot input must be regular file')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            return stream.read()
    finally:
        os.close(fd)

def diagnose(run_dir, provenance=None):
    """Capture inputs once, audit frozen copy, then compare that same copy.

    Provenance is caller attestation, NOT independently verified metadata:
    report_sha256, execution_id, environment_sha256, settings_sha256.
    It must describe one non-continuation execution. No provenance inference.
    """
    result = dict(kind='observed_baseline_label_diagnostic',
                  independent_verification_approval=False, cause='UNKNOWN',
                  provenance_verification='CALLER_ATTESTED_NOT_VERIFIED', groups=[],
                  auditor_sha256=AUDITOR_SHA256,
                  limitations=['Labels only, not probabilities or correctness equivalence',
                               'No model rerun or actual input/environment verification',
                               'Nondeterminism and pipeline drift are possible; cause unknown'])
    directory = Path(run_dir)
    # Refuse symlinks anywhere in the input directory path.
    if any(p.is_symlink() for p in (directory, *directory.parents)):
        raise ValueError('symlink directory forbidden')
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        report_bytes = read_leaf(fd, 'run.json')
        with tempfile.TemporaryDirectory() as td:
            frozen = Path(td)
            (frozen/'run.json').write_bytes(report_bytes)
            report = audit_module.read_json(frozen/'run.json')
            result['report_sha256'] = digest(report_bytes)
            settings = report.get('settings', {})
            if not isinstance(settings, dict):
                raise ValueError('settings must be an object')
            markers = ('resume_from', 'parent_run', 'continuation')
            # The pinned runner emits settings.resume_from=None for a fresh run.
            # Only this immediate null default is allowed; other markers stay conservative.
            nested_continuation = (settings.get('resume_from') is not None or
                                   any(k in settings for k in ('parent_run', 'continuation')))
            if any(k in report for k in markers) or nested_continuation or 'parent-run.json' in os.listdir(fd):
                result['status'] = 'NOT_COMPARABLE'
                result['reason'] = 'continuation excluded'
                return result
            blobs = {}
            for condition in report['conditions']:
                name = condition['csv']
                if name not in blobs:
                    blobs[name] = read_leaf(fd, name)
                if digest(blobs[name]) != condition['sha256']:
                    raise ValueError('CSV hash mismatch')
                (frozen/name).write_bytes(blobs[name])
            result['input_sha256'] = {k: digest(v) for k,v in sorted(blobs.items())}
            config_dir = frozen/'configs'
            config_dir.mkdir()
            result['config_sha256'] = {}
            for name in ('test_manifest.json', 'classes.json'):
                data = (ROOT/'configs'/name).read_bytes()
                (config_dir/name).write_bytes(data)
                result['config_sha256'][name] = digest(data)
            audit = audit_module.audit(frozen, frozen)
            result['per_condition_audit'] = audit['result']
            result['checked_conditions'] = len(report['conditions'])
            result['coverage_note'] = 'Only supplied audited conditions; missing conditions are not repeat evidence'
            required = ('execution_id', 'environment_sha256', 'settings_sha256')
            if not provenance or provenance.get('report_sha256') != result['report_sha256'] or any(not isinstance(provenance.get(k), str) or not provenance[k].strip() for k in required) or any(re.fullmatch('[0-9a-f]{64}', provenance.get(k, '')) is None for k in ('environment_sha256', 'settings_sha256')):
                result['status'] = 'INSUFFICIENT_PROVENANCE'
                return result
            result['attested_provenance'] = {k: provenance[k] for k in required}
            groups = {}
            for c in sorted(report['conditions'], key=lambda c:(c['model'],c['method'],c['epsilon'])):
                rows = list(csv.DictReader(io.StringIO(blobs[c['csv']].decode('utf-8'))))
                for pipeline in ('clean', 'defended_clean'):
                    key = (c['model'], c['model_sha256'], pipeline, c['method'] if pipeline == 'defended_clean' else '*')
                    groups.setdefault(key, []).append((c, rows))
            for key, entries in sorted(groups.items()):
                unique = {}; reused = 0
                for c, rows in entries:
                    if c['sha256'] in unique:
                        reused += 1
                    else:
                        unique[c['sha256']] = (c, rows)
                entries = list(unique.values())
                changed = set(); cells = 0
                if len(entries) > 1:
                    reference = entries[0][1]
                    for _, rows in entries[1:]:
                        for a,b in zip(reference, rows):
                            if a[key[2]+'_pred'] != b[key[2]+'_pred']:
                                changed.add(a['relative_path']); cells += 1
                result['groups'].append(dict(model=key[0], model_sha256=key[1], pipeline=key[2], filter=key[3],
                    declared_conditions=len(entries)+reused, distinct_csv_contents=len(entries), duplicate_content_conditions=reused, content_reuse_verified=False,
                    reference_comparisons=max(0,len(entries)-1), changed_comparison_cells=cells,
                    changed_unique_images=len(changed), comparison='SORTED_REFERENCE_NOT_ALL_PAIRS',
                    reason=('SINGLE_DISTINCT_CONTENT' if len(entries)<2 else 'OBSERVED_LABEL_COMPARISON'),
                    status=('NOT_COMPARABLE' if len(entries)<2 else 'MISMATCH' if changed else 'MATCHED_OBSERVED_BASELINE_LABELS')))
            result['status'] = 'DIAGNOSTIC_ONLY'
            return result
    finally:
        os.close(fd)
