"""Generate public verification status from hash-locked, scoped evidence.

Registry metadata is a reviewed declaration, not operator authentication. There is
no aggregate PASS: local reproduction never promotes external verification.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

REGISTRY = 'results/verification/status_registry.json'
SNAPSHOT = 'web/maris/public/evidence/verification-status.json'
START = '<!-- verification-status:start -->'
END = '<!-- verification-status:end -->'
PIPELINES = {'clean','defended_clean','attacked','transfer_defended','adaptive_defended'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def read_json(raw):
    def reject(value):
        raise ValueError('non-finite JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)


def read_evidence(root, entry):
    name = entry['path']
    p = PurePosixPath(name)
    require(not p.is_absolute() and p.as_posix() == name and '..' not in p.parts
            and name.startswith('results/verification/') and p.suffix == '.json', 'unsafe evidence path')
    path = root / name
    require(not any(part.is_symlink() for part in [path, *path.parents]), 'symlink evidence')
    raw = path.read_bytes()
    require(re.fullmatch('[0-9a-f]{64}', entry['sha256']) is not None, 'invalid hash')
    require(hashlib.sha256(raw).hexdigest() == entry['sha256'], 'evidence changed; review registry hash')
    return read_json(raw)


def local_status(record, evidence):
    require(record['operator_role'] == 'research_operator', 'local operator role')
    require(len(evidence) == 1, 'local evidence coverage')
    d = evidence[0]
    require(d['kind'] == 'received_pc_full_saved_output_audit', 'local evidence kind')
    require(d['independent_operator'] is False, 'local run cannot be independent')
    require(d['source_commit'] == record['source_commit'], 'source commit mismatch')
    require(d['local_status'] == 'LOCAL_PASS', 'unsupported local result')
    require(d['zip_crc_ok'] is True and d['reference_blobs_verified_at_source_commit'] is True
            and d['bundle_files_hash_verified'] == 35, 'incomplete receipt audit')
    require(d['probabilities_compared'] is False, 'probability scope changed')
    require(d['cause_confirmed'] is False, 'cause needs separate evidence')
    require(d['csv_files'] == 16 and d['rows_per_csv'] == 781
            and d['prediction_fields_per_row'] == 5 and d['prediction_cells_compared'] == 62480,
            'incomplete local coverage')
    require(d['metric_abs_tolerance'] == 1e-6 and d['linf_tolerance'] == 1e-6, 'tolerance changed')
    comparisons = d['comparisons_recomputed']
    require(len(comparisons) == 2 and {c['method'] for c in comparisons} == {'gaussian','mean'}, 'missing method')
    require(all(c['rows_compared'] == 6248 and c['status'] == 'PASS' and c['differences'] == []
                for c in comparisons), 'local comparison failed')
    return 'LOCAL_PASS', '전체 조건 기준 일치', '모델 2개·781장·두 필터·ε 4개. 라벨·요약 지표 비교 완료, 확률값 비교 제외.'


def external_status(record, evidence):
    require(record['operator_role'] == 'external_operator', 'external operator role')
    require(len(evidence) == 2, 'external evidence coverage')
    require({e['path'].split('/')[-1] for e in record['evidence']} ==
            {'gaussian_differences.json','mean_differences.json'}, 'external method coverage')
    count = 0
    for d in evidence:
        require(d['source_commit'] == record['source_commit'], 'source commit mismatch')
        require(d['kind'] == 'saved_label_diagnostic_not_stage_b_approval', 'external evidence kind')
        require(d['label_status'] == 'MISMATCH' and len(d['differences']) > 0, 'unsupported external result')
        expected = {f'{model}_eps_{eps:g}_samples.csv' for model in ('cnn','mobilenet') for eps in (0,.01,.03,.05)}
        conditions = d['conditions']
        require(len(conditions) == 8 and {c['file'] for c in conditions} == expected, 'external condition coverage')
        require(all(c['samples'] == 781 and set(c['pipelines']) == PIPELINES for c in conditions), 'external sample coverage')
        require(sum(p['label_differences'] for c in conditions for p in c['pipelines'].values()) == len(d['differences']), 'external difference counts')
        count += len(d['differences'])
    return 'FAIL', '기준과 일부 불일치', f'보존 결과에서 {count}개 예측 차이. 평균 필터는 보조 진단이며 외부 전체 검증 PASS가 아닙니다.'


def build(root):
    root = Path(root).resolve()
    raw = (root / REGISTRY).read_bytes()
    registry = read_json(raw)
    require(registry['schema_version'] == 1, 'unsupported registry')
    records = registry['records']
    require(len(records) == 2 and {r['id'] for r in records} == {'pc-full-20260928','external-01'}, 'registry coverage')
    cards = []
    adapters = {'pc-full-20260928': local_status, 'external-01': external_status}
    for record in records:
        require(re.fullmatch('[0-9a-f]{40}', record['source_commit']) is not None, 'invalid commit')
        require(re.fullmatch('[0-9a-f]{40}', record['evidence_revision']) is not None, 'invalid evidence revision')
        require(record['evidence'] and len({e['path'] for e in record['evidence']}) == len(record['evidence']), 'duplicate evidence')
        docs = [read_evidence(root, e) for e in record['evidence']]
        status, label, detail = adapters[record['id']](record, docs)
        require(record['status'] == status, 'status contradicts evidence')
        path = record['report_path']
        require(re.fullmatch(r'docs/[A-Z0-9_]+\.md', path) is not None and (root/path).is_file(), 'invalid report path')
        cards.append(dict(id=record['id'], title='연구 수행 PC 재현' if status=='LOCAL_PASS' else '외부 독립 재실행',
                          status=status, label=label, detail=detail,
                          evidence_url='https://github.com/heechan9/AdversarialAI_Security/blob/'+record['evidence_revision']+'/'+path))
    try:
        from .issue_lifecycle import build as build_issues
    except ImportError:
        from issue_lifecycle import build as build_issues
    issues = build_issues(root)
    return dict(schema_version=1, discrepancies=issues, registry_sha256=hashlib.sha256(raw).hexdigest(), cards=cards,
                cause_status='UNRESOLVED', cause_note='환경 간 차이의 정확한 원인은 미확정입니다. 로컬 일치를 외부 독립 검증 통과로 해석하지 않습니다.')


def markdown(snapshot):
    lines=[START, '| 검증 구분 | 상태 | 확인 범위 |', '|---|---|---|']
    for c in snapshot['cards']:
        lines.append(f"| [{c['title']}]({c['evidence_url']}) | {c['status']} | {c['detail']} |")
    lines += ['', snapshot['cause_note'], '', '| 추적 항목 | 처리 상태 | 이력 |', '|---|---|---|']
    for issue in snapshot['discrepancies']:
        lines.append(f"| {issue['title']} | {issue['label']} | {issue['event_count']}건 |")
    return '\n'.join(lines+[END])


def sync(root, write=False):
    root=Path(root)
    snapshot=build(root)
    expected=json.dumps(snapshot,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    readme=(root/'README.md').read_text(encoding='utf-8')
    require(readme.count(START)==readme.count(END)==1 and readme.index(START)<readme.index(END), 'README status markers')
    a,b=readme.index(START),readme.index(END)+len(END)
    updated=readme[:a]+markdown(snapshot)+readme[b:]
    if write:
        (root/SNAPSHOT).write_text(expected,encoding='utf-8')
        (root/'README.md').write_text(updated,encoding='utf-8')
    else:
        require((root/SNAPSHOT).read_text(encoding='utf-8')==expected, 'stale MARIS verification status')
        require(readme==updated, 'stale README verification status')
    return snapshot


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--write',action='store_true',help='Regenerate after evidence review; default is read-only check')
    args=parser.parse_args()
    sync(args.repo_root,args.write)
    print('Verification status evidence and generated displays agree; no inference performed.')


if __name__=='__main__':
    main()
