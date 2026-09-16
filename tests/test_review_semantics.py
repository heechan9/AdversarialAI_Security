from copy import deepcopy
from pathlib import Path
import pytest
from adversarial_ai.audit.exceptions import AuditError
from adversarial_ai.audit.review_semantics import summarize_followup_reviews
from adversarial_ai.audit.runner import run_full_audit


def record(meaning='description_confirmation'):
    return dict(sample_id='A/a.jpg', reviewer='reviewer', judgment='라벨 정확',
                meaning=meaning, meaning_source='explicit reviewer clarification')


def test_identical_words_do_not_make_mixed_meanings_compatible():
    a=record(); b=record('class_label_opinion'); b['sample_id']='B/b.jpg'
    with pytest.raises(AuditError, match='Mixed'):
        summarize_followup_reviews([a,b], meaning='description_confirmation')


@pytest.mark.parametrize('key,value', [('meaning',None),('meaning','unknown'),
    ('meaning',''),('meaning_source',' '),('meaning_source',None),('surprise','x')])
def test_missing_unknown_or_extra_semantics_fail_closed(key,value):
    a=record();a[key]=value
    with pytest.raises(AuditError):
        summarize_followup_reviews([a], meaning='description_confirmation')


def test_unknown_requested_meaning_and_empty_input_fail():
    for meaning,rows in [('unknown',[record()]),('description_confirmation',[])]:
        with pytest.raises(AuditError): summarize_followup_reviews(rows,meaning=meaning)


def test_raw_opinion_counts_are_not_ground_truth_and_inputs_unchanged():
    for meaning in ['description_confirmation','class_label_opinion']:
        rows=[record(meaning)];before=deepcopy(rows)
        out=summarize_followup_reviews(rows,meaning=meaning)
        assert out['raw_judgment_counts']=={'라벨 정확':1}
        assert out['label_correctness_verified'] is False
        assert rows==before
        with pytest.raises(AuditError,match='Duplicate'):
            summarize_followup_reviews(rows+rows,meaning=meaning)


def test_full_report_preserves_scope_boundary_without_writing():
    result=run_full_audit(repo_root=Path('.'))
    boundary=result['summary']['visual_review']['claim_boundary']
    assert boundary['scope']=='record_integrity_and_consistency'
    assert boundary['label_correctness_verified'] is False
    assert boundary['judgment_counts_meaning']=='verbatim_legacy_record_values'
    assert any('not label correctness' in s for s in result['verified_scopes'])
