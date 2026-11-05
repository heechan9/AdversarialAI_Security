"""Mutation checks for saved-result consistency; no private inputs or inference."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('matched_audit', ROOT / 'verification/matched_cnn_saved_audit.py')
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class SavedMatchedEvidence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / 'evidence'
        shutil.copytree(audit_module.DEFAULT, self.directory)

    def replace(self, name, value):
        """Refresh the local index so semantic checks, not just SHA checks, run."""
        path = self.directory / name
        path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
        index_path = self.directory / 'evidence-index.json'
        index = json.loads(index_path.read_text())
        index['files'][name]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        index_path.write_text(json.dumps(index))

    def report(self):
        return json.loads((self.directory / 'evaluation.json').read_text())

    def test_original_and_pre_inference_false_are_consistent(self):
        result = audit_module.audit(self.directory)
        self.assertEqual(result['mixed_minus_clean_only']['pgd50']['net_correct'], 7)
        self.assertFalse(result['independent_verification_approval'])

    def test_changed_csv_bytes_fail(self):
        path = self.directory / 'pgd_mixed.csv'
        path.write_bytes(path.read_bytes() + b'\r\n')
        with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
            audit_module.audit(self.directory)

    def test_summary_change_rejected_even_with_refreshed_index(self):
        report = self.report()
        report['models']['pgd_mixed']['attacks']['pgd50']['accuracy'] = .5
        self.replace('evaluation.json', report)
        with self.assertRaisesRegex(ValueError, 'Metric mismatch'):
            audit_module.audit(self.directory)

    def test_partial_samples_rejected(self):
        report = self.report()
        report['models']['clean_only']['samples'] = 780
        self.replace('evaluation.json', report)
        with self.assertRaisesRegex(ValueError, 'Incomplete/wrong model CSV'):
            audit_module.audit(self.directory)

    def test_running_rejected(self):
        report = self.report()
        report['status'] = 'RUNNING'
        self.replace('evaluation.json', report)
        with self.assertRaisesRegex(ValueError, 'Incomplete evaluation'):
            audit_module.audit(self.directory)

    def test_incorrect_recorded_checkpoint_rejected(self):
        report = self.report()
        report['models']['clean_only']['model_sha256'] = '0' * 64
        self.replace('evaluation.json', report)
        with self.assertRaisesRegex(ValueError, 'checkpoint metadata differs'):
            audit_module.audit(self.directory)

    def test_independent_approval_promotion_rejected(self):
        report = self.report()
        report['independent_verification_approval'] = True
        self.replace('evaluation.json', report)
        with self.assertRaisesRegex(ValueError, 'Approval boundary changed'):
            audit_module.audit(self.directory)


if __name__ == '__main__':
    unittest.main()
