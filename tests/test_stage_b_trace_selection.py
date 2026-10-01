import json
import tempfile
import unittest
from pathlib import Path

from verification.stage_b_trace import selected_groups


class SelectionTests(unittest.TestCase):
    def write(self, root, rows):
        p = Path(root)/'selection.json'
        p.write_text(json.dumps({'targeted_results': rows}))
        return p

    def row(self, index, reference, observed):
        return dict(row_index=index, reference=str(reference), observed_off=observed,
                    method='gaussian', pipeline='attacked', file='mobilenet_eps_0.03_samples.csv')

    def test_remaining_and_control_are_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            p=self.write(d,[self.row(25,7,7),self.row(99,1,6)])
            remaining=selected_groups(p)
            self.assertEqual(list(remaining),[('gaussian','attacked',.03,3)])
            self.assertEqual(list(selected_groups(p,25)),[('gaussian','attacked',.03,0)])

    def test_invalid_indices_fail(self):
        for index in (-1,781,True):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as d:
                with self.assertRaises(ValueError):
                    selected_groups(self.write(d,[self.row(index,1,6)]))

    def test_empty_selection_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                selected_groups(self.write(d,[self.row(25,7,7)]))


if __name__ == '__main__':
    unittest.main()
