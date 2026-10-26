"""Regression checks for the support packet's byte-identity blocker; no inference."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hyunsu_prepare', ROOT / 'verification/prepare_hyunsu_cross_inputs.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CrossInputPreparation(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.output = self.root / 'new-inputs'
        self.packet = self.root / 'packet.zip'
        self.canonical = {name: (ROOT / path).read_bytes() for name, (path, _) in module.PINS.items()}
        self.members = {name: b'template\n' for name in module.PACKET_MEMBERS - {'PACKAGE_SHA256.json'}}
        for name, data in self.canonical.items():
            key = 'verified_trace_reference.py' if name == 'stage_b_trace_b92ba8.py' else name
            self.members[key] = data + b'\n'
        self.refresh_packet()
        self.head, self.dirty = module.EVALUATION_SHA, b''
        def fake_git(repo, *args):
            if args == ('rev-parse', 'HEAD'):
                return (self.head + '\n').encode()
            if args == ('status', '--porcelain', '--untracked-files=no'):
                return self.dirty
            for name, (source, _) in module.PINS.items():
                if args == ('show', module.TOOL_SHA + ':' + source):
                    return self.canonical[name]
            raise AssertionError(args)
        self.git_patch = patch.object(module, 'git', side_effect=fake_git)
        self.git_patch.start()
        self.addCleanup(self.git_patch.stop)

    def refresh_packet(self):
        checks = {n: hashlib.sha256(b).hexdigest() for n, b in self.members.items()}
        with zipfile.ZipFile(self.packet, 'w') as archive:
            for name, data in self.members.items():
                archive.writestr(name, data)
            archive.writestr('PACKAGE_SHA256.json', json.dumps(checks))
        packet_hash = hashlib.sha256(self.packet.read_bytes()).hexdigest()
        if hasattr(self, 'packet_patch'):
            self.packet_patch.stop()
        self.packet_patch = patch.object(module, 'PACKET_SHA256', packet_hash)
        self.packet_patch.start()
        self.addCleanup(self.packet_patch.stop)

    def test_exact_inputs_and_no_execution_are_preserved(self):
        packet_before = self.packet.read_bytes()
        result = module.prepare(self.repo, self.packet, self.output)
        for name, data in self.canonical.items():
            self.assertEqual((self.output / name).read_bytes(), data)
        self.assertEqual(self.packet.read_bytes(), packet_before)
        self.assertEqual(result['status'], 'PREPARED_NOT_EXECUTED')
        self.assertEqual(result['support_verdict'], 'INCOMPLETE')
        self.assertFalse(result['model_inference_performed'])
        self.assertFalse(result['stage_b_approved'])
        self.assertEqual(len(list(self.output.iterdir())), 5)

    def test_original_extra_lf_reproduces_report_identity_blocker(self):
        saved_report_hash = module.PINS['selection.json'][1]
        supplied_hash = module.sha256(self.members['selection.json'])
        self.assertNotEqual(supplied_hash, saved_report_hash)
        module.prepare(self.repo, self.packet, self.output)
        self.assertEqual(module.sha256((self.output / 'selection.json').read_bytes()), saved_report_hash)

    def test_changed_packet_fails_before_writes(self):
        self.packet.write_bytes(self.packet.read_bytes() + b'changed')
        with self.assertRaisesRegex(ValueError, 'packet SHA-256 mismatch'):
            module.prepare(self.repo, self.packet, self.output)
        self.assertFalse(self.output.exists())

    def test_changed_selection_is_not_silently_normalized(self):
        self.members['selection.json'] = self.members['selection.json'].replace(b'491b973', b'0000000', 1)
        self.refresh_packet()
        with self.assertRaisesRegex(ValueError, 'Unexpected packet/source difference'):
            module.prepare(self.repo, self.packet, self.output)
        self.assertFalse(self.output.exists())

    def test_changed_pinned_source_is_rejected(self):
        self.canonical['stage_b_trace_b92ba8.py'] += b'# changed\n'
        with self.assertRaisesRegex(ValueError, 'Pinned public source hash mismatch'):
            module.prepare(self.repo, self.packet, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_is_not_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / 'keep'
        sentinel.write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            module.prepare(self.repo, self.packet, self.output)
        self.assertEqual(sentinel.read_bytes(), b'preserve')

    def test_wrong_checkout_or_dirty_source_is_rejected(self):
        self.head = module.TOOL_SHA
        with self.assertRaisesRegex(ValueError, '491b973'):
            module.prepare(self.repo, self.packet, self.output)
        self.head, self.dirty = module.EVALUATION_SHA, b' M tracked.py'
        with self.assertRaisesRegex(ValueError, 'tracked changes'):
            module.prepare(self.repo, self.packet, self.output)
        self.assertFalse(self.output.exists())

    def test_output_inside_checkout_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            module.prepare(self.repo, self.packet, self.repo / 'new-output')


if __name__ == '__main__':
    unittest.main()
