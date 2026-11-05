import copy
import unittest
from worst_class_review import summarize


def row(name, n, d, s, a):
    return dict(class_name=name, N=n, D=d, B=n-d, S=s, ASR=s/d if d else None,
                attacked_correct=a, attacked_accuracy=a/n,
                clean_wrong_to_attacked_correct=a-d+s)

class WorstClassTests(unittest.TestCase):
    def test_clean_errors_not_attack_successes(self):
        out=summarize([row('weak',10,1,1,0),row('large',100,90,50,40)])
        self.assertEqual(out['minimum_attacked_accuracy']['classes'],['weak'])
        self.assertEqual(out['maximum_conditional_ASR']['classes'],['weak'])
        self.assertEqual(out['worst_attacked_details'][0]['B'],9)
        self.assertEqual(out['worst_attacked_details'][0]['S'],1)
    def test_zero_denominator_is_not_zero_asr(self):
        out=summarize([row('none',10,0,0,2)])
        self.assertIsNone(out['maximum_conditional_ASR']['value'])
        self.assertEqual(out['maximum_conditional_ASR']['classes'],[])
        self.assertEqual(out['undefined_ASR_classes'],['none'])
    def test_ties_preserved_and_order_independent(self):
        rows=[row('z',10,5,5,0),row('a',20,10,10,0)]
        self.assertEqual(summarize(rows),summarize(rows[::-1]))
        self.assertEqual(summarize(rows)['minimum_attacked_accuracy']['classes'],['a','z'])
    def test_clean_accuracy_separate(self):
        out=summarize([row('a',10,8,8,0),row('b',10,1,0,1)])
        self.assertEqual(out['minimum_clean_accuracy']['classes'],['b'])
        self.assertEqual(out['minimum_attacked_accuracy']['classes'],['a'])
    def test_empty_and_duplicate_rejected(self):
        for rows in ([],[row('a',10,5,2,3)]*2):
            with self.subTest(rows=rows),self.assertRaises(ValueError):summarize(rows)
    def test_invalid_counts_rejected(self):
        for field,value in [('N',0),('D',11),('S',-1),('N',True),('attacked_correct',11),('B',0)]:
            r=row('a',10,5,2,3);r[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):summarize([r])
    def test_derived_rate_or_transition_tampering_rejected(self):
        for field,value in [('ASR',float('nan')),('ASR',0.9),('attacked_accuracy',1),('clean_wrong_to_attacked_correct',1)]:
            r=row('a',10,5,2,3);r[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):summarize([r])
    def test_recovery_is_valid_and_exposed(self):
        out=summarize([row('a',10,5,2,5)])
        self.assertEqual(out['worst_attacked_details'][0]['clean_wrong_to_attacked_correct'],2)

if __name__=='__main__':unittest.main()
