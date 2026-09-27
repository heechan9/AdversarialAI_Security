"""Check runtime versions and H5 loading before the full rerun; no inference."""
import argparse
import json
import sys
from pathlib import Path

from verification.stage_b_readiness import _load_json, _sha256


def validate_versions(python_version, tensorflow_version, keras_version):
    if tuple(python_version[:2]) != (3, 11):
        raise ValueError('Use the documented Python 3.11 environment')
    if tensorflow_version != '2.21.0' or keras_version != '3.15.1':
        raise ValueError('Expected TensorFlow 2.21.0 and Keras 3.15.1 from requirements.txt')


def preflight(root, contract):
    import tensorflow as tf
    import keras
    validate_versions(sys.version_info, tf.__version__, keras.__version__)
    loaded = []
    for spec in contract['models']:
        path = root/spec['path']
        metadata = _load_json(root/'results/clean'/f"{spec['id']}_metadata.json")
        if _sha256(path) != spec['sha256'] or spec['sha256'] != metadata['model_sha256']:
            raise ValueError('model hash differs before loading')
        model = tf.keras.models.load_model(path)
        try:
            if list(model.input_shape[1:]) != spec['input_shape'] or model.output_shape[-1] != 10:
                raise ValueError('model input/output shape differs')
            loaded.append(spec['id'])
        finally:
            del model
            tf.keras.backend.clear_session()
    return dict(status='PASS', tensorflow=tf.__version__, keras=keras.__version__,
                models_loaded=loaded, inference_performed=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(preflight(Path.cwd(), _load_json(args.contract)), indent=2))
