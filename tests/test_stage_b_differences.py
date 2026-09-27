import csv
import shutil
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch
from verification.stage_b_differences import compare
from verification import stage_b_onednn_diagnostic as diagnostic

ROOT=Path(__file__).resolve().parents[1]


def check_differences(tmp_path):
    ref=ROOT/'results/defenses/experimental/gaussian_run_01'
    actual=tmp_path/'actual';shutil.copytree(ref,actual)
    assert compare(ref,actual)['label_status']=='MATCH'
    path=actual/'mobilenet_eps_0.01_samples.csv'
    with path.open(newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    for i in (25,71): rows[i]['adaptive_defended_pred']=str((int(rows[i]['adaptive_defended_pred'])+1)%10)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    before=path.read_bytes()
    report=compare(ref,actual)
    assert len(report['differences'])==2
    assert report['unique_affected_images']==2
    assert path.read_bytes()==before


def check_invalid(tmp_path,mutation):
    ref=ROOT/'results/defenses/experimental/gaussian_run_01'
    actual=tmp_path/'actual';shutil.copytree(ref,actual)
    path=actual/'cnn_eps_0_samples.csv'
    with path.open(newline='') as f:
        reader=csv.DictReader(f);fields=reader.fieldnames;rows=list(reader)
    if mutation=='missing': rows.pop()
    if mutation=='nan': rows[0]['original_linf']='nan'
    if mutation=='duplicate': rows[1]['relative_path']=rows[0]['relative_path']
    if mutation=='label': rows[0]['true_index']='10'
    if mutation=='order': rows[0],rows[1]=rows[1],rows[0]
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    with unittest.TestCase().assertRaises(ValueError):compare(ref,actual)


def check_controlled(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    def check(cmd,**kw):
        return diagnostic.BASE if cmd[:3]==['git','rev-parse','HEAD'] else ''

    calls=[]
    def run(cmd,**kw):
        calls.append(kw['env']);return type('Result',(),{'returncode':0})()
    with patch.object(diagnostic.subprocess,'check_output',check), patch.object(diagnostic.subprocess,'run',run):
        diagnostic.run(root,tmp_path/'outputs')
        with unittest.TestCase().assertRaises(FileExistsError): diagnostic.run(root,tmp_path/'outputs')
    assert [e['TF_ENABLE_ONEDNN_OPTS'] for e in calls]==['1','1','0','0']
    assert {k:v for k,v in calls[0].items() if k!='TF_ENABLE_ONEDNN_OPTS'}=={k:v for k,v in calls[-1].items() if k!='TF_ENABLE_ONEDNN_OPTS'}


class DiagnosticsTests(unittest.TestCase):
    def test_differences(self):
        with tempfile.TemporaryDirectory() as d: check_differences(Path(d))
    def test_invalid(self):
        for mutation in ['missing','nan','duplicate','label','order']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as d:
                check_invalid(Path(d),mutation)
    def test_controlled(self):
        with tempfile.TemporaryDirectory() as d: check_controlled(Path(d))

if __name__ == '__main__': unittest.main()
