import importlib.util
import io
import json
from pathlib import Path
import shutil
import zipfile
import pytest

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('independent_gaussian',REPO/'scripts/audit_gaussian_defense.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_archived_run():
    assert module.audit(REPO,REPO/'results/defenses/experimental/gaussian_run_01')['status']=='PASSED'


@pytest.fixture
def evidence(tmp_path):
    return Path(shutil.copytree(REPO/'results/defenses/experimental/gaussian_run_01',tmp_path/'evidence'))


def repack(root):
    """Re-sign hashes too: semantic checks must still reject mutations."""
    checks=json.loads((root/'SHA256.json').read_text())
    for name in checks: checks[name]=module.digest((root/name).read_bytes())
    (root/'SHA256.json').write_text(json.dumps(checks))
    c=json.loads((root/'COMPLETE.json').read_text());c['summary_sha256']=checks['summary.json'];c['checksums_sha256']=module.digest((root/'SHA256.json').read_bytes())
    (root/'COMPLETE.json').write_text(json.dumps(c))
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        for name in list(checks)+['SHA256.json','COMPLETE.json']:z.writestr('run/'+name,(root/name).read_bytes())
    (root/'original_bundle.zip').write_bytes(b.getvalue())
    p=json.loads((root/'PROVENANCE.json').read_text());p['original_bundle_sha256']=module.digest(b.getvalue())
    (root/'PROVENANCE.json').write_text(json.dumps(p))


@pytest.mark.parametrize('change',['denominator','class','extra','zero','nonfinite','schema','promoted'])
def test_semantic_mutations_even_with_updated_hashes(evidence,change):
    if change in ['denominator','class','extra']:
        p=evidence/'summary.json';s=json.loads(p.read_text())
        if change=='denominator':s[0]['overall']['asr_adaptive_defended']['denominator']+=1
        if change=='class':next(iter(s[0]['classes'].values()))['samples']+=1
        if change=='extra':s.append(s[0])
        p.write_text(json.dumps(s))
    elif change=='promoted':
        p=evidence/'COMPLETE.json';s=json.loads(p.read_text());s['promoted']=True;p.write_text(json.dumps(s))
    else:
        p=evidence/'cnn_eps_0_samples.csv';s=p.read_text()
        if change=='schema':s=s.replace('adaptive_linf','bad_column')
        else:
            lines=s.splitlines();row=lines[1].split(',');row[-1]='0.0000001' if change=='zero' else 'nan';lines[1]=','.join(row);s='\n'.join(lines)+'\n'
        p.write_text(s)
    repack(evidence)
    with pytest.raises(ValueError):module.audit(REPO,evidence)


def test_archive_bytes_cannot_silently_change(evidence):
    with (evidence/'summary.json').open('ab') as f:f.write(b' ')
    with pytest.raises(ValueError,match='archive member mismatch'):module.audit(REPO,evidence)


def test_duplicate_json_and_nonfinite_fail():
    for raw in ['{"a":1,"a":2}','{"a":NaN}']:
        with pytest.raises(ValueError):module.document(raw)


@pytest.mark.parametrize('change', ['hash', 'missing', 'extra', 'empty', 'type'])
def test_source_contract_mutation_rehashed(evidence, change):
    p = evidence / 'contract.json'
    contract = json.loads(p.read_text())
    sources = contract['source_files']
    key = sorted(module.SOURCE_PATHS)[0]
    if change == 'hash': sources[key] = '0' * 64
    elif change == 'missing': del sources[key]
    elif change == 'extra': sources['../escape.py'] = '0' * 64
    elif change == 'empty': contract['source_files'] = {}
    else: sources[key] = True
    p.write_text(json.dumps(contract))
    repack(evidence)
    with pytest.raises(ValueError, match='source'):
        module.audit(REPO, evidence)


@pytest.mark.parametrize('crlf', [False, True])
def test_source_line_endings_and_actual_change(tmp_path, crlf):
    sources = {}
    for name in module.SOURCE_PATHS:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'line1\r\nline2\r\n' if crlf else b'line1\nline2\n')
        sources[name] = module.digest(b'line1\r\nline2\r\n')
    module.verify_sources(tmp_path, sources)
    path.write_bytes(path.read_bytes() + b'# changed')
    with pytest.raises(ValueError, match='source file mismatch'):
        module.verify_sources(tmp_path, sources)


def test_missing_source_file(tmp_path):
    with pytest.raises(OSError):
        module.verify_sources(tmp_path, {p: '0' * 64 for p in module.SOURCE_PATHS})


def replace_archive(root, entries, compression=zipfile.ZIP_DEFLATED):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=compression) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    raw = buffer.getvalue()
    (root/'original_bundle.zip').write_bytes(raw)
    provenance = json.loads((root/'PROVENANCE.json').read_text())
    provenance['original_bundle_sha256'] = module.digest(raw)
    (root/'PROVENANCE.json').write_text(json.dumps(provenance))


@pytest.mark.parametrize('change', ['count', 'member_size', 'total_size', 'codec', 'path', 'duplicate'])
def test_archive_policy_rejects_before_decompression(evidence, monkeypatch, change):
    with zipfile.ZipFile(evidence/'original_bundle.zip') as archive:
        entries = [(item.filename, archive.read(item)) for item in archive.infolist()]
    compression = zipfile.ZIP_DEFLATED
    if change == 'count':
        entries.append(('run/extra.json', b'{}'))
    elif change == 'member_size':
        entries[0] = (entries[0][0], b'0' * 1_000_001)
    elif change == 'total_size':
        entries = [(name, b'0' * 200_000) for name, _ in entries]
    elif change == 'codec':
        compression = zipfile.ZIP_BZIP2
    elif change == 'path':
        entries[-1] = ('../bad.json', b'{}')
    else:
        entries[-1] = ('other/' + entries[0][0].replace('\\', '/').split('/')[-1], b'{}')
    replace_archive(evidence, entries, compression)
    def unexpected_open(*args, **kwargs):
        pytest.fail('rejected archive reached decompression')
    monkeypatch.setattr(zipfile.ZipFile, 'open', unexpected_open)
    with pytest.raises(ValueError):
        module.audit(REPO, evidence)


@pytest.mark.parametrize('filename,size', [('PROVENANCE.json', 65_537), ('original_bundle.zip', 2_000_001)])
def test_oversized_input_rejected_before_zip_parse(evidence, monkeypatch, filename, size):
    (evidence/filename).write_bytes(b' ' * size)
    def unexpected_parse(*args, **kwargs):
        pytest.fail('oversized file reached ZIP parsing')
    monkeypatch.setattr(zipfile, 'ZipFile', unexpected_parse)
    with pytest.raises(ValueError, match='size limit'):
        module.audit(REPO, evidence)


def test_oversized_loose_evidence(evidence):
    (evidence/'summary.json').write_bytes(b' ' * 1_000_001)
    with pytest.raises(ValueError, match='size limit'):
        module.audit(REPO, evidence)


@pytest.mark.parametrize('compression', [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_benign_repack_remains_valid(evidence, compression):
    with zipfile.ZipFile(evidence/'original_bundle.zip') as archive:
        entries = [(item.filename, archive.read(item)) for item in archive.infolist()]
    replace_archive(evidence, entries, compression)
    assert module.audit(REPO, evidence)['status'] == 'PASSED'


def test_corrupt_crc_rejected(evidence):
    with zipfile.ZipFile(evidence/'original_bundle.zip') as archive:
        entries = [(item.filename, archive.read(item)) for item in archive.infolist()]
    replace_archive(evidence, entries, zipfile.ZIP_STORED)
    raw = bytearray((evidence/'original_bundle.zip').read_bytes())
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        info = archive.infolist()[0]
        offset = info.header_offset
        name_length = int.from_bytes(raw[offset+26:offset+28], 'little')
        extra_length = int.from_bytes(raw[offset+28:offset+30], 'little')
        raw[offset+30+name_length+extra_length] ^= 1
    (evidence/'original_bundle.zip').write_bytes(raw)
    provenance = json.loads((evidence/'PROVENANCE.json').read_text())
    provenance['original_bundle_sha256'] = module.digest(raw)
    (evidence/'PROVENANCE.json').write_text(json.dumps(provenance))
    with pytest.raises(zipfile.BadZipFile):
        module.audit(REPO, evidence)


def test_zip64_data_descriptor_repack_remains_valid(evidence):
    class NonSeekable(io.BytesIO):
        def seek(self, *args):
            raise io.UnsupportedOperation('streaming ZIP')
    with zipfile.ZipFile(evidence/'original_bundle.zip') as archive:
        entries = [(item.filename, archive.read(item)) for item in archive.infolist()]
    buffer = NonSeekable()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            with archive.open(name, 'w', force_zip64=True) as stream:
                stream.write(data)
    raw = buffer.getvalue()
    (evidence/'original_bundle.zip').write_bytes(raw)
    provenance = json.loads((evidence/'PROVENANCE.json').read_text())
    provenance['original_bundle_sha256'] = module.digest(raw)
    (evidence/'PROVENANCE.json').write_text(json.dumps(provenance))
    assert module.audit(REPO, evidence)['status'] == 'PASSED'


def test_forged_uncompressed_size_rejected(evidence):
    raw = bytearray((evidence/'original_bundle.zip').read_bytes())
    offset = raw.index(b'PK\x01\x02')
    # Underreport the first member size in the central directory. A bounded
    # read must still verify the member CRC rather than trust this metadata.
    raw[offset+24:offset+28] = (1).to_bytes(4, 'little')
    (evidence/'original_bundle.zip').write_bytes(raw)
    provenance = json.loads((evidence/'PROVENANCE.json').read_text())
    provenance['original_bundle_sha256'] = module.digest(raw)
    (evidence/'PROVENANCE.json').write_text(json.dumps(provenance))
    with pytest.raises(zipfile.BadZipFile):
        module.audit(REPO, evidence)


def test_wide_short_csv_rejects_first_row_without_amplification(monkeypatch):
    reader = module.csv.reader
    def guarded_reader(*args, **kwargs):
        for number, row in enumerate(reader(*args, **kwargs)):
            if number > 1:
                pytest.fail('malformed CSV continued beyond first invalid row')
            yield row
    monkeypatch.setattr(module.csv, 'reader', guarded_reader)
    raw = (','.join(f'c{i}' for i in range(500)) + '\n' + 'x\n' * 1000).encode()
    with pytest.raises(ValueError, match='CSV width'):
        module.rows(raw)


@pytest.mark.parametrize('change', ['wide_header', 'excess_rows'])
def test_rehashed_csv_resource_mutation_rejected(evidence, change):
    path = evidence/'cnn_eps_0_samples.csv'
    if change == 'wide_header':
        path.write_text(','.join(f'c{i}' for i in range(500)) + '\n' + 'x\n' * 1000)
        expected = 'CSV schema'
    else:
        content = path.read_text()
        path.write_text(content + content.splitlines()[1] + '\n')
        expected = 'CSV row count'
    repack(evidence)
    with pytest.raises(ValueError, match=expected):
        module.audit(REPO, evidence)
