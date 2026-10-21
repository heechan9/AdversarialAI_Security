from verification.summarize_bim import public_metrics


def test_harm_is_not_net_accuracy_drop_and_common_population():
    rows=[dict(true_index='0',clean_pred=c,defended_clean_pred=d,attacked_pred='1',transfer_defended_pred='1',adaptive_defended_pred='1')
          for c,d in [('0','1'),('1','0'),('1','0'),('0','0')]]
    metrics={p:dict(accuracy=.5,asr=.5,asr_successes=1,asr_denominator=2) for p in
             ('clean','defended_clean','attacked','transfer_defended','adaptive_defended')}
    out={r['pipeline']:r for r in public_metrics(dict(model='fixture',method='mean',epsilon=.01,metrics=metrics),rows)}
    assert out['defended_clean']['asr'] is None
    assert out['defended_clean']['filter_harm_rate']==.5
    assert out['defended_clean']['filter_recovery_rate']==1
    assert out['defended_clean']['net_clean_accuracy_change']==.25
    assert out['adaptive_defended']['common_clean_denominator']==1
    assert out['adaptive_defended']['common_clean_asr']==1
