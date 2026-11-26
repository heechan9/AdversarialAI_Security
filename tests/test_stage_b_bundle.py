import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from verification.stage_b_bundle import audit, digest


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'run.log').write_text('original')
        self.report = {'status': 'INTERRUPTED', 'artifact_sha256': {'run.log': digest(self.root / 'run.log')}}
        self.save()

    def save(self):
        (self.root / 'rerun-report.json').write_text(json.dumps(self.report))

    def test_integrity_does_not_promote_interrupted_run(self):
        result = audit(self.root)
        self.assertEqual(result['integrity_status'], 'PASS')
        self.assertEqual(result['recorded_execution_status'], 'INTERRUPTED')

    def test_added_removed_and_changed(self):
        (self.root / 'run.log').write_text('modified')
        self.assertEqual(audit(self.root)['changed'], ['run.log'])
        (self.root / 'run.log').unlink()
        (self.root / 'extra.txt').write_text('extra')
        result = audit(self.root)
        self.assertEqual(result['removed'], ['run.log'])
        self.assertEqual(result['added'], ['extra.txt'])
        self.assertEqual(result['integrity_status'], 'FAIL')

    def test_external_report_hash_detects_coordinated_change(self):
        trusted = digest(self.root / 'rerun-report.json')
        self.assertTrue(audit(self.root, trusted)['report_hash_reference_checked'])
        self.report['status'] = 'PASS'
        self.save()
        with self.assertRaises(ValueError):
            audit(self.root, trusted)

    def test_report_is_opened_once_for_hashing_and_parsing(self):
        report_path = self.root / 'rerun-report.json'
        trusted = digest(report_path)
        open_path = Path.open
        modes = []

        def track_open(path, mode='r', *args, **kwargs):
            if path == report_path.resolve():
                modes.append(mode)
            return open_path(path, mode, *args, **kwargs)

        with patch.object(Path, 'open', track_open):
            result = audit(self.root, trusted)
        self.assertEqual(modes, ['rb'])
        self.assertEqual(result['report_sha256'], trusted)
        self.assertEqual(result['recorded_execution_status'], 'INTERRUPTED')

    def test_oversized_report_is_rejected_before_parsing(self):
        report_path = self.root / 'rerun-report.json'
        with patch('verification.stage_b_bundle.MAX_REPORT_BYTES', report_path.stat().st_size - 1):
            with self.assertRaisesRegex(ValueError, 'size limit'):
                audit(self.root)

    def test_bad_paths_and_hashes(self):
        for path in ('../outside', '/outside', 'a\\b', 'C:/outside', './run.log', 'rerun-report.json'):
            self.report['artifact_sha256'] = {path: '0' * 64}
            self.save()
            with self.assertRaises(ValueError):
                audit(self.root)
        self.report['artifact_sha256'] = {'run.log': 'bad'}
        self.save()
        with self.assertRaises(ValueError):
            audit(self.root)

    def test_empty_duplicate_and_nonfinite_json(self):
        for content in ('{"artifact_sha256":{}}', '{"status":1,"status":2}', '{"status":NaN}', '[]'):
            (self.root / 'rerun-report.json').write_text(content)
            with self.assertRaises(ValueError):
                audit(self.root)

    def test_symlink_rejected(self):
        try:
            (self.root / 'link').symlink_to(self.root / 'run.log')
        except OSError:
            self.skipTest('symlinks unavailable')
        with self.assertRaises(ValueError):
            audit(self.root)


if __name__ == '__main__':
    unittest.main()
