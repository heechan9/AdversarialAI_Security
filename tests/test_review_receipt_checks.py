from dataclasses import asdict, replace
from itertools import permutations
import unittest

from verification.review_receipt_checks import A,B,C,D,E,Receipt,audit_ledger,current_context,recovery_trace,report,unique_receipts


class Checks(unittest.TestCase):
    def test_bad_schema_or_bad_boolean_rejected(self):
        for mutation in ({"schema":True},{"schema":2},{"completed":"false"},{"step":True},
                         {"state":"unknown"},{"extra":1}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                Receipt.read({**asdict(A),**mutation})

    def test_wrong_session_or_revision_is_historical(self):
        self.assertTrue(current_context(A,"review-a",2))
        self.assertFalse(current_context(A,"review-b",2))
        self.assertFalse(current_context(A,"review-a",3))

    def test_repeat_is_one_but_conflict_stops(self):
        self.assertEqual(unique_receipts([A,A,B,A]),(A,B))
        self.assertEqual(len(unique_receipts([A,replace(A,revision=3)])),2)
        with self.assertRaisesRegex(ValueError,"conflicting"):
            unique_receipts([A,replace(A,state="reviewable")])

    def test_recovery_steps_gap_and_fresh_confirmation(self):
        self.assertEqual([x["state"] for x in recovery_trace([A,B,C,D,E])],
                         ["hold","hold","reviewable","hold","reviewable"])
        self.assertEqual(recovery_trace([A,B,replace(C,completed=False)])[-1]["state"],"hold")
        for items in ([A,B,B],[A,C,B],[A,replace(B,revision=3)]):
            with self.subTest(items=items),self.assertRaises(ValueError):
                recovery_trace(items)

    def test_all_raw_rows_explained_no_conflict_leak(self):
        ledger=report()["receipt_ledger"]
        self.assertEqual(ledger["n_raw"],7)
        self.assertEqual(ledger["counts"],{"conflicting_receipt":3,"eligible_for_trace":2,
                         "historical_context":1,"invalid_receipt":1})
        self.assertEqual([x["row"] for x in ledger["ledger"]],list(range(1,8)))
        samples=[asdict(B),asdict(C),asdict(replace(B,state="hold"))]
        for order in permutations(samples):
            self.assertEqual(audit_ledger(order,"review-a",2)["counts"],
                             {"conflicting_receipt":2,"eligible_for_trace":1})

    def test_clean_repeat_remains_explicit_in_ledger(self):
        self.assertEqual(audit_ledger([asdict(A),asdict(A)],"review-a",2)["counts"],
                         {"eligible_for_trace":1,"repeat_not_counted":1})
