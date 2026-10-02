import copy
import json
from pathlib import Path
import pytest
from verification.subset_sensitivity import recalculate, subsets

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/extensions/sensitivity/20261002'


def test_locked_subset_membership_and_fail_closed_groups():
    manifest=json.loads((BASE/'subsets.json').read_text())
    test=json.loads((ROOT/'configs/test_manifest.json').read_text())
    result=subsets(manifest,test)
    assert {k:len(v) for k,v in result.items()}=={'full_781':781,'source_train_disjoint':771,'unique_test_rgb':775,'source_train_disjoint_unique':767}
    assert result['source_train_disjoint_unique']==result['source_train_disjoint']&result['unique_test_rgb']
    invalid=copy.deepcopy(manifest);invalid['test_exact_rgb_duplicate_groups'].append(invalid['test_exact_rgb_duplicate_groups'][0])
    with pytest.raises(ValueError,match='overlapping'):subsets(invalid,test)
    invalid=copy.deepcopy(manifest);invalid['source_train_overlap_test_paths'].remove('Bulkers/Bulkers_1037.jpeg')
    with pytest.raises(ValueError,match='all identical'):subsets(invalid,test)


@pytest.mark.parametrize('attack',['bim','pgd'])
def test_saved_results_recompute_without_promoting_partial(attack):
    report=recalculate(ROOT/f'results/extensions/checkpoints/20261002-pc/{attack}',BASE/'subsets.json',ROOT)
    assert report==json.loads((BASE/f'{attack}-partial.json').read_text())
    assert report['scope']=='PARTIAL_OUTPUTS_ONLY'
    assert report['independent_verification_approval'] is False
    for condition in report['conditions']:
        for view,metrics in condition['subsets'].items():
            for metric in metrics.values():
                assert metric['samples']==report['subset_counts'][view]
                assert metric['accuracy']==metric['correct']/metric['samples']
