import ast
import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('colab_inputs',ROOT/'verification/colab_inputs.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class Drive:
    def __init__(self,pages):self.pages=iter(pages);self.calls=[]
    def files(self):return self
    def list(self,**kwargs):self.calls.append(kwargs);return self
    def execute(self):return next(self.pages)


def test_shared_file_on_second_page():
    f=dict(id='example',name=m.ARCHIVE_NAME,size='123',md5Checksum='hash',mimeType='application/zip')
    service=Drive([{'files':[],'nextPageToken':'page2'},{'files':[f]}])
    assert m.find_archive(service)==f
    assert service.calls[1]['pageToken']=='page2'
    assert all(c['includeItemsFromAllDrives'] and c['supportsAllDrives'] for c in service.calls)


def test_missing_and_conflicting_copies():
    with pytest.raises(FileNotFoundError):m.find_archive(Drive([{}]))
    files=[dict(id='a',size='1',md5Checksum='a'),dict(id='b',size='1',md5Checksum='b')]
    with pytest.raises(ValueError,match='서로 다른'):m.find_archive(Drive([{'files':files}]))
    files[1]['md5Checksum']='a'
    assert m.find_archive(Drive([{'files':files}]))['id']=='a'


def test_notebook_cells_parse_and_fail_with_helpful_order_error():
    notebook=json.loads((ROOT/'notebooks/AdversarialAI_Mobile_GPU.ipynb').read_text())
    codes=[''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code']
    for code in codes:ast.parse(code)
    for code in codes[1:]:
        with pytest.raises(AssertionError,match='먼저'):exec(code,{})
