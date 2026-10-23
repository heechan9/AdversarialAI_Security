"""Regression: verification must remain active under optimized Python."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=Path(os.environ.get('ADVERSARIAL_CHECKOUT',HERE.parent/'adversarial_acceptance_20261023'))

class CsvVerifierTests(unittest.TestCase):
    def run_verifier(self, optimized, packet):
        return subprocess.run([sys.executable]+(['-O'] if optimized else [])+
            [str(HERE/'verify_saved_csv.py'),str(ROOT),str(packet)],capture_output=True,text=True)
    def test_valid_normal(self):self.check_valid(False)
    def test_valid_optimized(self):self.check_valid(True)
    def check_valid(self, optimized):
        result=self.run_verifier(optimized,HERE/'input-classwise-review.json')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['class_rows_recounted_from_saved_predictions'],80)
        self.assertEqual(json.loads(result.stdout)['status'],'PASS')
    def test_tampered_normal(self):self.check_tampered(False)
    def test_tampered_optimized(self):self.check_tampered(True)
    def check_tampered(self,optimized):
        packet=json.loads((HERE/'input-classwise-review.json').read_text(encoding='utf-8'))
        packet['classes'][0]['N']=999
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'tampered.json';target.write_text(json.dumps(packet),encoding='utf-8')
            result=self.run_verifier(optimized,target)
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertNotIn('"status": "PASS"',result.stdout)

if __name__=='__main__':unittest.main()
