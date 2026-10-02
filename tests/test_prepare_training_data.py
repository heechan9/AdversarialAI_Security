import hashlib
import pytest
from verification.prepare_training_data import exclusion_plan,verify_downloads


def row(path,pixel,raw=None):
    return {'path':path,'pixel_sha256':pixel,'sha256':raw or pixel}


def report(train,valid=None,test=None):
    return {'decode_errors':[], 'splits':{'train':{'files':train},
        'valid':{'files':valid or []},'test':{'files':test or []}}}


def test_removes_held_out_conflicting_labels_and_reencoded_copies():
    data=report([row('A/1.jpg','one'),row('A/2.png','one','reencoded'),
                 row('A/conflict.jpg','shared'),row('B/conflict.jpg','shared'),
                 row('A/leak.png','held-out','different-format'),row('B/keep.jpg','unique')],
                test=[row('test.jpg','held-out')])
    retained,excluded=exclusion_plan(data)
    assert retained==['A/1.jpg','B/keep.jpg']
    reasons={r['path']:r['reasons'] for r in excluded}
    assert reasons['A/2.png']==['within_train_exact_duplicate']
    assert reasons['A/conflict.jpg']==reasons['B/conflict.jpg']==['conflicting_training_labels']
    assert reasons['A/leak.png']==['held_out_exact_overlap']


def test_held_out_data_and_decode_failures_are_not_silently_repaired():
    with pytest.raises(ValueError,match='validation/test overlap'):
        exclusion_plan(report([],valid=[row('v','same')],test=[row('t','same')]))
    with pytest.raises(ValueError,match='validation duplicates'):
        exclusion_plan(report([],valid=[row('v1','same'),row('v2','same')]))
    data=report([]);data['decode_errors']=[{'path':'bad.jpg'}]
    with pytest.raises(ValueError,match='decoding failed'):exclusion_plan(data)


def test_incomplete_duplicate_or_changed_downloads_fail_closed(tmp_path):
    p=tmp_path/'one.jpg';p.write_bytes(b'example')
    source=[{'id':'first'}];staged=[{'id':'first','path':'one.jpg','bytes':7,
        'sha256':hashlib.sha256(b'example').hexdigest()}]
    verify_downloads(source,staged,tmp_path,1)
    with pytest.raises(ValueError,match='download inventory'):verify_downloads(source,[],tmp_path,1)
    with pytest.raises(ValueError,match='source inventory'):verify_downloads(source,staged,tmp_path,2)
    p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='staged bytes'):verify_downloads(source,staged,tmp_path,1)
