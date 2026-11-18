"""Revision operands rejected before git; synthetic reports only."""
import importlib.util,json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('guarded_cont',ROOT/'src/adversarial_ai/evaluation/continuation.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
@pytest.mark.parametrize('which',['parent','report'])
@pytest.mark.parametrize('bad',['--output=harmless.txt','-R','HEAD','a'*39,'g'*40,None,[],{},'a'*40+'\n'])
def test_bad_revision_rejected_before_git(tmp_path,monkeypatch,which,bad):
 source=tmp_path/'source';source.mkdir();out=tmp_path/'out';out.mkdir()
 parent={'source_commit':'a'*40};report={'source_commit':'b'*40}
 (parent if which=='parent' else report)['source_commit']=bad
 (source/'run.json').write_text(json.dumps(parent));before=(source/'run.json').read_bytes()
 def forbidden(*a,**k):raise AssertionError('git must not be called')
 monkeypatch.setattr(m.subprocess,'check_output',forbidden)
 with pytest.raises(ValueError,match='invalid '+which+' source_commit'):
  m.carry_forward(source,out,report,tmp_path)
 assert not list(out.iterdir()) and (source/'run.json').read_bytes()==before
