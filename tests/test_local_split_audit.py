from PIL import Image
import pytest
from verification.local_split_audit import audit_splits


def test_decoded_duplicates_and_split_overlap(tmp_path):
    train = tmp_path/'train'; valid = tmp_path/'valid'
    train.mkdir(); valid.mkdir()
    image = Image.new('RGB', (2, 3), (20, 30, 40))
    image.save(train/'one.png', compress_level=0)
    image.save(train/'two.png', compress_level=9)
    image.save(valid/'held-out.png')
    result = audit_splits({'train': train, 'valid': valid})
    assert result['splits']['train']['duplicate_groups']['sha256'] == []
    assert result['splits']['train']['duplicate_groups']['pixel_sha256'] == [['one.png', 'two.png']]
    assert len(result['cross_split_duplicates']['pixel_sha256']) == 1
    assert result['training_ready'] is False


def test_image_shape_corruption_and_missing_split(tmp_path):
    Image.new('RGB', (2, 3)).save(tmp_path/'one.png')
    Image.new('RGB', (3, 2)).save(tmp_path/'two.png')
    (tmp_path/'bad.jpg').write_bytes(b'not an image')
    result = audit_splits({'train': tmp_path})
    assert result['splits']['train']['count'] == 2
    assert result['splits']['train']['duplicate_groups']['pixel_sha256'] == []
    assert result['decode_errors'][0]['path'] == 'bad.jpg'
    with pytest.raises(ValueError, match='missing split'):
        audit_splits({'train': tmp_path/'absent'})
