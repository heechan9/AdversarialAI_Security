import copy
import json
from pathlib import Path
import tempfile
import unittest
from paired_defense_review import align, index_rows, summarize, transitions, review

HERE = Path(__file__).resolve().parent

class PairedReviewTests(unittest.TestCase):
    def setUp(self):
        self.classes = {'0':'A', '1':'B'}
        self.manifest = {'test_samples':2, 'test_files':[
            {'relative_path':'A/a.jpg','label':'A'}, {'relative_path':'B/b.jpg','label':'B'}]}
        self.a = [{'relative_path':p,'epsilon':'0.03','true_index':t,
                   'clean_predicted_index':c,'adversarial_predicted_index':q}
                  for p,t,c,q in [('A\\a.jpg','0','0','1'),('B/b.jpg','1','0','1')]]
        self.d = [{'relative_path':p,'epsilon':'0.03','true_index':t,
                   'clean_pred':c,'attacked_pred':q,'defended_clean_pred':dc,
                   'transfer_defended_pred':tr,'adaptive_defended_pred':ad,
                   'original_linf':'0.03','adaptive_linf':'0.03'}
                  for p,t,c,q,dc,tr,ad in [('A/a.jpg','0','0','1','1','0','1'),
                                          ('B/b.jpg','1','0','1','1','1','0')]]
    def aligned(self):
        return align(self.a,self.d,self.manifest,self.classes,.03)
    def test_order_and_separator_alignment(self):
        expected=self.aligned();self.d.reverse()
        self.assertEqual(self.aligned(),expected)
    def test_denominators_do_not_mix(self):
        r=summarize(self.aligned())
        self.assertEqual(r['asr_own_clean_sets_not_paired']['plain'],
                         {'successes':1,'clean_correct_denominator':1,'asr':1.0})
        self.assertEqual(r['common_clean_correct_subset']['n'],0)
        self.assertIsNone(r['common_clean_correct_subset']['adaptive']['asr'])
        self.assertEqual(r['attack_plain_to_transfer_defended']['gained'],1)
        self.assertEqual(r['attack_plain_to_adaptive_defended']['lost'],1)
    def test_transitions_exact(self):
        r=transitions([True,True,False,False],[True,False,True,False])
        self.assertEqual([r[k] for k in ('both_correct','both_wrong','gained','lost')],[1]*4)
        self.assertEqual(r['b_minus_a_percentage_points'],0)
    def test_duplicate_normalized_paths(self):
        self.a.append(dict(self.a[0],relative_path='A/a.jpg'))
        with self.assertRaisesRegex(ValueError,'duplicate'): self.aligned()
    def test_missing_manifest_image(self):
        self.d.pop()
        with self.assertRaisesRegex(ValueError,'coverage'): self.aligned()
    def test_truth_mismatch(self):
        self.d[0]['true_index']='1'
        with self.assertRaisesRegex(ValueError,'truth'): self.aligned()
    def test_changed_baseline(self):
        self.d[0]['clean_pred']='1'
        with self.assertRaisesRegex(ValueError,'unpaired'): self.aligned()
    def test_nonfinite_epsilon(self):
        self.d[0]['epsilon']='nan'
        with self.assertRaisesRegex(ValueError,'epsilon'): self.aligned()
    def test_invalid_prediction(self):
        self.d[0]['adaptive_defended_pred']='99'
        with self.assertRaisesRegex(ValueError,'predicted'): self.aligned()
    def test_nonfinite_and_excess_perturbations(self):
        for value in ['nan','inf','-0.01','0.031']:
            with self.subTest(value=value):
                self.d[0]['adaptive_linf']=value
                with self.assertRaisesRegex(ValueError,'perturbation'): self.aligned()
    def test_zero_epsilon_identity(self):
        for row in self.a+self.d: row['epsilon']='0'
        for row in self.d: row['original_linf']=row['adaptive_linf']='0'
        with self.assertRaisesRegex(ValueError,'zero-budget'):align(self.a,self.d,self.manifest,self.classes,0)
    def test_empty_and_unsafe_paths(self):
        for path in ['', '../a', '/a', 'a//b','C:/a']:
            with self.subTest(path=path),self.assertRaises(ValueError):index_rows([{'relative_path':path}])
        with self.assertRaises(ValueError):summarize([])
    def test_pin_change_fails_closed(self):
        pin=json.loads((HERE/'source_pin.json').read_text())
        pin['files'][0]['git_blob_sha1']='0'*40
        with self.assertRaisesRegex(ValueError,'pin mismatch'):review(HERE.parents[1],pin)
    def test_saved_evidence_and_aggregation(self):
        result=review(HERE.parents[1],json.loads((HERE/'source_pin.json').read_text()))
        self.assertEqual(len(result['conditions']),16)
        self.assertFalse(result['independent_units_verified'])
        self.assertIsNone(result['inference']['mcnemar_p'])
        self.assertIsNone(result['inference']['bootstrap_ci'])
        for c in result['conditions']:
            groups=c['by_class'].values(); overall=c['overall']
            self.assertEqual(overall['n'],781)
            self.assertEqual(sum(g['n'] for g in groups),781)
            for k in ['clean_plain_to_defended','attack_plain_to_transfer_defended',
                      'attack_plain_to_adaptive_defended','defended_transfer_to_adaptive']:
                for count in ['a_correct','b_correct','both_correct','both_wrong','gained','lost']:
                    self.assertEqual(sum(g[k][count] for g in groups),overall[k][count])
            for kind in ['plain','transfer','adaptive']:
                for count in ['successes','clean_correct_denominator']:
                    self.assertEqual(sum(g['asr_own_clean_sets_not_paired'][kind][count] for g in groups),
                                     overall['asr_own_clean_sets_not_paired'][kind][count])
        self.assertEqual(result,json.loads((HERE/'paired-defense-results.json').read_text()))

if __name__=='__main__':unittest.main()
