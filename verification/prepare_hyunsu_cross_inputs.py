"""Prepare byte-exact public diagnostic inputs; never import/run a model."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


EVALUATION_SHA = '491b973cd9f4840664044a83c0d62d1ee1bb98e8'
TOOL_SHA = 'b92ba8f450020479198a8bb03dbfa510044d6c19'
PACKET_SHA256 = 'd6fd80b6419f0aaf59081e1a9245cc967fca04798ca379939da1bdf1ee1527b4'
PINS = {
    'selection.json': (
        'results/verification/stage_b/hyeonsu_01_review/local_followup.json',
        '8fc81a4408d6e43d5321bf9df2d416401a5b30df0af96a095d348496fcf6d52b'),
    'stage_b_trace_b92ba8.py': (
        'verification/stage_b_trace.py',
        '78ad7acb5289a2890ffe3365e27039c054c599d0f1c818252ecd28523a3c162b'),
    'expected_manifest.json': (
        'configs/test_manifest.json',
        '36059fea372334509404aca0e66155bf99a8df270beb1cc3bf4865b361ae70a6'),
}
PACKET_MEMBERS = {
    'expected_manifest.json', '02_결과보고_양식.md', 'asset_check.py',
    '01_작업안내.md', 'verified_trace_reference.py', 'PACKAGE_SHA256.json',
    'selection.json', '00_현수에게_보낼말.txt', 'diff_template.csv',
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def prepare(repo, packet, output):
    repo, packet, output = Path(repo).resolve(), Path(packet).resolve(), Path(output).resolve()
    if output.is_relative_to(repo) or repo.is_relative_to(output):
        raise ValueError('Use a fresh output directory outside the evaluation checkout')
    if output.exists():
        raise ValueError('Output already exists; choose a new directory')
    if git(repo, 'rev-parse', 'HEAD').decode().strip() != EVALUATION_SHA:
        raise ValueError('Use the unchanged 491b973 evaluation checkout')
    if git(repo, 'status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('Evaluation checkout has tracked changes')
    raw = packet.read_bytes()
    if sha256(raw) != PACKET_SHA256:
        raise ValueError('Support packet SHA-256 mismatch; original packet required')
    payloads, identities = {}, {}
    with zipfile.ZipFile(packet) as archive:
        names = archive.namelist()
        if len(names) != len(PACKET_MEMBERS) or set(names) != PACKET_MEMBERS:
            raise ValueError('Unexpected support packet members')
        checks = json.loads(archive.read('PACKAGE_SHA256.json'))
        if set(checks) != PACKET_MEMBERS - {'PACKAGE_SHA256.json'}:
            raise ValueError('Incomplete support packet checksum inventory')
        for name, expected in checks.items():
            if sha256(archive.read(name)) != expected:
                raise ValueError('Support packet member hash mismatch: ' + name)
        for name, (source_path, expected) in PINS.items():
            canonical = git(repo, 'show', TOOL_SHA + ':' + source_path)
            if sha256(canonical) != expected:
                raise ValueError('Pinned public source hash mismatch: ' + name)
            packet_name = 'verified_trace_reference.py' if name == 'stage_b_trace_b92ba8.py' else name
            supplied = archive.read(packet_name)
            # This known packet added one LF to each of these three public files.
            # Preserve it as evidence; never normalize a returned execution report.
            if supplied != canonical + b'\n':
                raise ValueError('Unexpected packet/source difference: ' + packet_name)
            payloads[name] = canonical
            identities[name] = dict(source_path=source_path, sha256=expected,
                                    original_packet_sha256=sha256(supplied),
                                    difference='one extra trailing LF in original packet')
        payloads['asset_check.py'] = archive.read('asset_check.py')
        identities['asset_check.py'] = dict(sha256=sha256(payloads['asset_check.py']),
                                            source='unchanged original support packet')
    result = dict(kind='HYUNSU_CROSS_INPUT_PREPARATION', status='PREPARED_NOT_EXECUTED',
                  evaluation_sha=EVALUATION_SHA, diagnostic_tool_source_sha=TOOL_SHA,
                  original_packet_sha256=PACKET_SHA256, files=identities,
                  model_inference_performed=False, stage_b_approved=False,
                  support_verdict='INCOMPLETE',
                  remaining='Executor asset report, cross-only results, commands, environment and logs required')
    output.mkdir(parents=True, exist_ok=False)
    for name, data in payloads.items():
        with (output / name).open('xb') as stream:
            stream.write(data)
    with (output / 'preparation.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = prepare(args.repo, args.packet, args.output)
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        parser.exit(2, 'INCOMPLETE: ' + str(exc) + '\n')
    print(result['status'] + '; no inference or reproduction approval')


if __name__ == '__main__':
    main()
