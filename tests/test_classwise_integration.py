"""Reject class maps that would silently drop or merge ASR denominators."""
import numpy as np
import pytest
from adversarial_ai.evaluation.fgsm_evaluation import compute_classwise_untargeted_asr


@pytest.mark.parametrize('values,names', [([0,2], ['a','b']), ([0,-1], ['a','b']), ([0.,1.], ['a','b']), ([[0,1]], ['a','b']), ([0,1], ['a','a']), ([0,1], ['a',''])])
def test_invalid_classwise_inputs_are_rejected(values, names):
    values = np.asarray(values)
    with pytest.raises(ValueError):
        compute_classwise_untargeted_asr(values, values, values, names)
