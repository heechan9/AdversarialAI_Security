"""Check runtime versions and H5 loading before the full rerun; no inference."""
import argparse
import json
import sys
import shutil
from tempfile import TemporaryDirectory
from pathlib import Path

if __package__:
    from .stage_b_readiness import _load_json, _safe_path, _sha256
else:
    from stage_b_readiness import _load_json, _safe_path, _sha256


def validate_versions(python_version, tensorflow_version, keras_version):
    if tuple(python_version[:2]) != (3, 11):
        raise ValueError('Use the documented Python 3.11 environment')
    if tensorflow_version != '2.21.0' or keras_version != '3.15.1':
        raise ValueError('Expected TensorFlow 2.21.0 and Keras 3.15.1 from requirements.txt')


def snapshot_models(root, contract, snapshot_root):
    for spec in contract['models']:
        source = _safe_path(root, spec['path'])
        target = _safe_path(snapshot_root, spec['path'])
        if source is None or target is None or not source.is_file():
            raise ValueError('invalid model path for Stage B snapshot')
        target.parent.mkdir(parents=True, exist_ok=True)
        with source.open('rb') as original, target.open('xb') as snapshot:
            shutil.copyfileobj(original, snapshot)
        if _sha256(target) != spec['sha256']:
            raise ValueError('model snapshot hash differs before loading')


def preflight(root, contract, model_snapshot_root=None):
    if model_snapshot_root is None:
        with TemporaryDirectory(prefix='stage-b-models-') as directory:
            snapshot_root = Path(directory)
            snapshot_models(root, contract, snapshot_root)
            return preflight(root, contract, snapshot_root)
    import tensorflow as tf
    import keras
    validate_versions(sys.version_info, tf.__version__, keras.__version__)
    loaded = []
    for spec in contract['models']:
        path = _safe_path(model_snapshot_root, spec['path'])
        if path is None:
            raise ValueError('invalid model snapshot path')
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
    parser.add_argument('--model-snapshot-root', type=Path)
    args = parser.parse_args()
    print(json.dumps(preflight(Path.cwd(), _load_json(args.contract), args.model_snapshot_root), indent=2))
