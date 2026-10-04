import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from verification.stage_b_original_environment import matches_recorded, manifest_rows, run, package_evidence


class OriginalEnvironmentTests(unittest.TestCase):
    def test_version_gate_does_not_accept_linux_or_new_python(self):
        expected=dict(system='Windows',python='3.11.15',tensorflow='2.21.0',keras='3.15.1')
        self.assertTrue(matches_recorded(expected))
        self.assertFalse(matches_recorded(dict(expected,system='Linux')))
        self.assertFalse(matches_recorded(dict(expected,python='3.12.14')))

    def test_manifest_rejects_duplicates_and_escape(self):
        entries=[{'relative_path':f'Class/{i}.jpg'} for i in range(781)]
        self.assertEqual(len(manifest_rows(dict(test_samples=781,test_files=entries))),781)
        for bad in ('../escape.jpg','C:/escape.jpg','/escape.jpg','Class\\escape.jpg','Class/1.jpg'):
            rows=[dict(x) for x in entries];rows[0]['relative_path']=bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                manifest_rows(dict(test_samples=781,test_files=rows))

    def test_failed_gate_preserves_report_and_stops_before_copy(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            args=SimpleNamespace(source_repo=root/'repo',models_dir=root/'models',data_dir=root/'data',
                output=root/'output',execute=True,require_recorded_environment=True)
            with patch('verification.stage_b_original_environment.inventory',return_value={'system':'Linux'}),patch('verification.stage_b_original_environment.verify_and_copy') as copy:
                with self.assertRaises(ValueError):run(args)
                copy.assert_not_called()
            report=json.loads((root/'output/evidence/run-report.json').read_text())
            self.assertEqual(report['status'],'INCOMPLETE')
            self.assertFalse(report['inference_performed'])
            self.assertFalse(report['stage_b_approved'])
            self.assertTrue((root/'output/return-evidence.zip').is_file())
            with self.assertRaises(FileExistsError):run(args)

    def test_output_must_not_overlap_inputs(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            args=SimpleNamespace(source_repo=root/'repo',models_dir=root/'models',data_dir=root/'data',output=root/'repo/output')
            with self.assertRaises(ValueError):run(args)
            self.assertFalse(args.output.exists())

    def test_native_settings_and_checkpoint_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            args=SimpleNamespace(source_repo=root/'repo',models_dir=root/'models',data_dir=root/'data',
                output=root/'output',execute=True,require_recorded_environment=False)
            def child(command,**kwargs):
                self.assertEqual(kwargs['env']['TF_ENABLE_ONEDNN_OPTS'],'0')
                self.assertEqual(kwargs['env']['TF_NUM_INTRAOP_THREADS'],'3')
                checkpoint=json.loads((args.output/'evidence/run-report.json').read_text())
                self.assertEqual(checkpoint['status'],'TRACE_RUNNING_NOT_COMPLETE')
                self.assertIsNone(checkpoint['inference_performed'])
                out=Path(command[command.index('--output')+1]);out.mkdir()
                result={'execution_status':'COMPLETE','weights_unchanged':True,'results':[
                    {'key':str(i),'selected':[{'reference':'1','actual':'6'}],'native':[{'prediction':6}]} for i in range(5)]}
                (out/'report.json').write_text(json.dumps(result))
                return SimpleNamespace(returncode=0)
            with patch.dict(os.environ,{'TF_ENABLE_ONEDNN_OPTS':'0','TF_NUM_INTRAOP_THREADS':'3'}),patch('verification.stage_b_original_environment.inventory',return_value={'system':'Linux'}),patch('verification.stage_b_original_environment.verify_and_copy',return_value={'models_verified':2,'images_verified':781}),patch('verification.stage_b_original_environment.subprocess.run',side_effect=child):
                run(args)
                self.assertEqual(os.environ['TF_ENABLE_ONEDNN_OPTS'],'0')
            report=json.loads((args.output/'evidence/run-report.json').read_text())
            self.assertEqual(report['status'],'TRACE_COMPLETE_NOT_APPROVED')
            self.assertFalse(report['original_environment_identity_proven'])

    def test_failed_child_does_not_claim_no_inference(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            args=SimpleNamespace(source_repo=root/'repo',models_dir=root/'models',data_dir=root/'data',
                output=root/'output',execute=True,require_recorded_environment=False)
            with patch('verification.stage_b_original_environment.inventory',return_value={'system':'Linux'}),patch('verification.stage_b_original_environment.verify_and_copy',return_value={'models_verified':2,'images_verified':781}),patch('verification.stage_b_original_environment.subprocess.run',return_value=SimpleNamespace(returncode=1)):
                with self.assertRaises(RuntimeError):run(args)
            report=json.loads((args.output/'evidence/run-report.json').read_text())
            self.assertIsNone(report['inference_performed'])
            self.assertEqual(report['status'],'INCOMPLETE')

    def test_archive_is_complete_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);evidence=root/'evidence';evidence.mkdir()
            (evidence/'sample.bin').write_bytes(bytes(range(256))*100)
            archive=root/'return.zip'
            package_evidence(evidence,archive)
            with zipfile.ZipFile(archive) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(z.read('sample.bin'),(evidence/'sample.bin').read_bytes())
            self.assertFalse(list(root.glob('*.partial')))
            with self.assertRaises(FileExistsError):package_evidence(evidence,archive)


if __name__=='__main__':unittest.main()
