"""Carry forward audited whole conditions with explicit source lineage."""
import hashlib
import json
from pathlib import Path
import subprocess


def carry_forward(source, out, report, root):
    from verification.iterative_result_audit import audit
    source, out, root = Path(source), Path(out), Path(root)
    # Freeze report bytes before copying; audit the frozen inputs, not a moving run.
    parent_bytes = (source/'run.json').read_bytes()
    parent = json.loads(parent_bytes)
    if parent['kind'] != 'followup_iterative_evaluation' or report['kind'] != parent['kind']:
        raise ValueError('continuation supports original models only')
    for key in ('attack','steps','step_size','restarts','seed','batch_size'):
        if parent['settings'][key] != report['settings'][key]:
            raise ValueError('continuation setting mismatch: '+key)
    for key in ('python','platform','tensorflow','keras','numpy','environment','manifest_sha256','classes_sha256'):
        if parent[key] != report[key]:
            raise ValueError('continuation environment/input mismatch: '+key)
    # Runner bookkeeping can change; its attack/filter/integrity dependencies
    # and configuration must be byte-identical to the parent commit.
    dependencies = ['configs','src/adversarial_ai/attacks/iterative.py','src/adversarial_ai/attacks/fgsm.py','src/adversarial_ai/defenses','src/adversarial_ai/evaluation/integrity.py','src/adversarial_ai/__init__.py','src/adversarial_ai/attacks/__init__.py','src/adversarial_ai/evaluation/__init__.py']
    changed = subprocess.check_output(['git','diff','--name-only',parent['source_commit'],report['source_commit'],'--',*dependencies],cwd=root,text=True).splitlines()
    allowed = {'src/adversarial_ai/evaluation/iterative_evaluation.py','src/adversarial_ai/evaluation/continuation.py'}
    if set(changed)-allowed:
        raise ValueError('attack/inference source differs from parent')
    import tempfile
    with tempfile.TemporaryDirectory(dir=out) as temporary:
        frozen=Path(temporary);(frozen/'run.json').write_bytes(parent_bytes)
        if 'continuation' in parent:
            if (source/'parent-run.json').is_symlink():raise ValueError('parent report symlink forbidden')
            (frozen/'parent-run.json').write_bytes((source/'parent-run.json').read_bytes())
        for condition in parent['conditions']:
            name=condition['csv']
            if Path(name).name!=name or '/' in name or '\\' in name or (source/name).is_symlink():
                raise ValueError('unsafe continuation CSV')
            (frozen/name).write_bytes((source/name).read_bytes())
        audit(frozen,root)
        for condition in parent['conditions']:
            (out/condition['csv']).write_bytes((frozen/condition['csv']).read_bytes())
    (out/'parent-run.json').write_bytes(parent_bytes)
    report['continuation'] = {
        'parent_report_sha256': hashlib.sha256(parent_bytes).hexdigest(),
        'parent_source_commit': parent['source_commit'],
        'inherited_conditions': len(parent['conditions']),
        'note': 'Whole conditions inherited from the audited parent; remaining conditions use this report source commit. Not an independent rerun.',
    }
    report['conditions'] = parent['conditions']
    return {(v['model'],v['method'],v['epsilon']) for v in parent['conditions']}
