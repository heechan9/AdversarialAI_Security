"""Saved-data diagnostic behavior and fail-closed export checks; no model execution."""
import csv
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'verification/matched_cnn_diagnostics.py'
spec = importlib.util.spec_from_file_location('cnn_diagnostics', SCRIPT)
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


class MatchedCnnDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = diagnostics.build_report(outcome='all')

    def test_real_transition_cases_and_metrics_match_saved_results(self):
        report = diagnostics.build_report()
        self.assertEqual(len(report['cases']), 49)
        paired = report['selected']['mixed_vs_clean_only']
        self.assertEqual([paired[k] for k in ('newly_correct', 'newly_incorrect',
                         'both_correct', 'both_wrong', 'net_correct')], [28, 21, 20, 712, 7])
        c = report['selected']['models']['pgd_mixed']
        self.assertEqual((c['samples'], c['correct'], c['own_clean_asr_successes'],
                          c['own_clean_asr_denominator']), (781, 48, 492, 540))
        # Outcome selection must not shrink the denominator to the 49 changed cases.
        self.assertEqual(report['selection']['exported_cases'], 49)
        self.assertEqual(report['selected']['samples'], 781)

    def test_every_exported_case_is_traceable_to_its_paired_predictions(self):
        self.assertEqual(len({c['relative_path'] for c in self.report['cases']}), 781)
        for case in self.report['cases']:
            b = case['clean_only_condition_pred'] == case['true_index']
            c = case['pgd_mixed_condition_pred'] == case['true_index']
            expected = ('both_correct' if b and c else 'both_wrong' if not b and not c
                        else 'newly_correct' if c else 'newly_incorrect')
            self.assertEqual(case['outcome'], expected)

    def test_class_counts_sum_to_overall_counts(self):
        report = self.report
        self.assertEqual(len(report['by_class']), 10)
        self.assertEqual(sum(c['samples'] for c in report['by_class']), 781)
        for model in diagnostics.MODELS:
            for field in ('correct', 'clean_correct', 'own_clean_asr_successes',
                          'own_clean_asr_denominator'):
                self.assertEqual(sum(c['models'][model][field] for c in report['by_class']),
                                 report['overall']['models'][model][field])
        for outcome in ('newly_correct', 'newly_incorrect', 'both_correct', 'both_wrong'):
            self.assertEqual(sum(c['mixed_vs_clean_only'][outcome] for c in report['by_class']),
                             report['overall']['mixed_vs_clean_only'][outcome])

    def test_class_and_outcome_filters_keep_metric_scope_separate(self):
        report = diagnostics.build_report(class_name='Container Ship', outcome='newly_incorrect')
        group = next(c for c in self.report['by_class'] if c['true_class'] == 'Container Ship')
        self.assertEqual(report['selected']['samples'], group['samples'])
        self.assertEqual(report['selected']['models'], group['models'])
        self.assertEqual(len(report['cases']), group['mixed_vs_clean_only']['newly_incorrect'])
        self.assertEqual(len(report['cases']), 6)
        self.assertTrue(all(c['true_class'] == 'Container Ship' and c['outcome'] == 'newly_incorrect'
                            for c in report['cases']))
        self.assertEqual(report['overall'], self.report['overall'])

    def test_empty_case_filter_preserves_population_and_csv_headers(self):
        report = diagnostics.build_report(class_name='Tug', outcome='newly_incorrect')
        self.assertEqual(report['cases'], [])
        self.assertEqual(report['selected']['samples'], 68)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'empty'
            diagnostics.export_report(report, output)
            with (output / 'cases.csv').open(encoding='utf-8', newline='') as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(reader.fieldnames, list(diagnostics.CASE_FIELDS))
                self.assertEqual(list(reader), [])

    def test_common_clean_denominator_is_explicit_and_distinct(self):
        common = self.report['overall']['common_clean_correct_asr']
        self.assertEqual(common['samples'], 518)
        self.assertEqual(common['models']['clean_only']['successes'], 477)
        self.assertEqual(common['models']['pgd_mixed']['successes'], 470)
        self.assertNotEqual(common['samples'],
                            self.report['overall']['models']['pgd_mixed']['own_clean_asr_denominator'])

    def test_clean_condition_does_not_invent_attack_success_rates(self):
        report = diagnostics.build_report(condition='clean')
        self.assertEqual(report['selected']['mixed_vs_clean_only']['net_correct'], 1)
        for metric in report['overall']['models'].values():
            self.assertIsNone(metric['own_clean_asr'])
            self.assertIsNone(metric['own_clean_asr_successes'])
            self.assertIsNone(metric['own_clean_asr_denominator'])
        for metric in report['overall']['common_clean_correct_asr']['models'].values():
            self.assertIsNone(metric['asr'])

    def test_zero_denominators_are_null_including_empty_groups(self):
        case = dict(true_index=0, outcome='both_wrong')
        for model in diagnostics.MODELS:
            case[f'{model}_clean_pred'] = 1
            case[f'{model}_condition_pred'] = 1
        for cases in ([case], []):
            summary = diagnostics.describe(cases, 'pgd50')
            for model in diagnostics.MODELS:
                self.assertEqual(summary['models'][model]['own_clean_asr_denominator'], 0)
                self.assertIsNone(summary['models'][model]['own_clean_asr'])
            self.assertEqual(summary['common_clean_correct_asr']['samples'], 0)
            self.assertIsNone(summary['common_clean_correct_asr']['models']['clean_only']['asr'])
        self.assertIsNone(diagnostics.describe([], 'pgd50')['models']['baseline']['accuracy'])

    def test_pgd7_is_its_own_recorded_condition(self):
        report = diagnostics.build_report(condition='pgd7')
        self.assertEqual(report['selected']['models']['pgd_mixed']['correct'], 148)
        self.assertEqual(report['selected']['models']['pgd_mixed']['own_clean_asr_successes'], 392)
        self.assertEqual(report['selected']['mixed_vs_clean_only']['newly_correct'], 80)
        self.assertEqual(report['selected']['mixed_vs_clean_only']['newly_incorrect'], 22)

    def test_invalid_selections_are_rejected(self):
        for kwargs in ({'condition': 'fgsm'}, {'outcome': 'recovered'}, {'class_name': 'unknown'}):
            with self.assertRaises(ValueError):
                diagnostics.build_report(**kwargs)

    def test_existing_failure_and_approval_boundaries_are_retained(self):
        boundaries = self.report['boundaries']
        self.assertFalse(boundaries['independent_verification_approval'])
        self.assertFalse(boundaries['statistical_inference_performed'])
        self.assertFalse(boundaries['historical_training_manifests_recovered'])
        self.assertEqual(boundaries['existing_external_stage_b'], 'FAIL')
        self.assertEqual(boundaries['hyunsu_selected_diagnostic'], 'INCOMPLETE')

    def test_deterministic_json_and_csv_exports_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            first, second = Path(temp) / 'first', Path(temp) / 'second'
            report = diagnostics.build_report()
            diagnostics.export_report(report, first)
            diagnostics.export_report(report, second)
            for name in ('report.json', 'cases.csv'):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            with (first / 'cases.csv').open(encoding='utf-8', newline='') as stream:
                cases = list(csv.DictReader(stream))
            self.assertEqual(len(cases), 49)
            self.assertEqual({c['outcome'] for c in cases}, {'newly_correct', 'newly_incorrect'})
            self.assertEqual(json.loads((first / 'report.json').read_text())['selected']['samples'], 781)
            before = (first / 'report.json').read_bytes()
            with self.assertRaises(FileExistsError):
                diagnostics.export_report(report, first)
            self.assertEqual((first / 'report.json').read_bytes(), before)

    def test_corrupt_input_blocks_cli_before_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            directory, output = Path(temp) / 'evidence', Path(temp) / 'output'
            shutil.copytree(diagnostics.DEFAULT, directory)
            path = directory / 'pgd_mixed.csv'
            path.write_bytes(path.read_bytes() + b'\n')
            result = subprocess.run([sys.executable, str(SCRIPT), '--directory', str(directory),
                                     '--output-dir', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('DIAGNOSTICS_BLOCKED', result.stderr)
            self.assertIn('SHA mismatch', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
