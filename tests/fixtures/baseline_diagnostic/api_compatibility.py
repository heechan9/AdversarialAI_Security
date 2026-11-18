"""Frozen-main / PR119 auditor API comparison; synthetic CSVs only."""
import copy, importlib.util, json, hashlib
from pathlib import Path
import pytest
from test_iterative_result_audit import case
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=load('old_auditor',ROOT/'tests/fixtures/frozen_v2/verification/iterative_result_audit.py')
new=load('new_auditor',ROOT/'verification/iterative_result_audit.py')
@pytest.mark.parametrize('mode',['partial','complete','zero','hash','metric','duplicate','invalid_status'])
def test_noncontinuation_equivalent(case,mode):
 folder,r=case
 if mode=='complete':r['status']='COMPLETED_NOT_INDEPENDENT_APPROVAL'
 elif mode=='zero':r['conditions']=[]
 elif mode=='hash':r['conditions'][0]['sha256']='0'*64
 elif mode=='metric':r['conditions'][0]['metrics']['clean']['accuracy']=0.2
 elif mode=='duplicate':r['conditions'].append(copy.deepcopy(r['conditions'][0]))
 elif mode=='invalid_status':r['status']='PASS'
 (folder/'run.json').write_text(json.dumps(r))
 before={p.name:p.read_bytes() for p in folder.iterdir()}
 def outcome(m):
  try:return ('return',m.audit(folder,ROOT))
  except Exception as e:return ('error',type(e).__name__,str(e))
 assert outcome(old)==outcome(new)
 assert before=={p.name:p.read_bytes() for p in folder.iterdir()}
 assert old.PIPELINES==new.PIPELINES
@pytest.mark.parametrize('text',['{"x":1,"x":2}','{"x":NaN}','{"x":1}'])
def test_read_json_equivalent(tmp_path,text):
 p=tmp_path/'x.json';p.write_text(text)
 def outcome(m):
  try:return ('return',m.read_json(p))
  except Exception as e:return ('error',type(e).__name__,str(e))
 assert outcome(old)==outcome(new)
