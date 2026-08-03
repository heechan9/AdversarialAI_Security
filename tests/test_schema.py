"""
Mock schema validation test for the multimodal API output contract.

This test does NOT call any real API. It only validates that (a) a
well-formed mock response matches the required JSON Schema, and (b) a
malformed response (invalid class, missing field) is correctly rejected.
See configs/api_poc.yaml for the schema definition this mirrors.
"""
import json
from pathlib import Path

import jsonschema
import pytest
import yaml

CONFIG_PATH = Path(__file__).resolve().parents[1] / "configs" / "api_poc.yaml"


@pytest.fixture(scope="module")
def output_schema():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config["output_schema"]


def test_valid_mock_response_passes(output_schema):
    mock_response = {
        "predicted_class": "Container Ship",
        "reason": "Long flat deck stacked with rectangular containers.",
        "uncertain": False,
        "attack_suspected": False,
    }
    jsonschema.validate(instance=mock_response, schema=output_schema)


def test_out_of_enum_class_is_rejected(output_schema):
    mock_response = {
        "predicted_class": "Fishing Boat",  # not in the 10-class enum
        "reason": "n/a",
        "uncertain": False,
        "attack_suspected": False,
    }
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=mock_response, schema=output_schema)


def test_missing_required_field_is_rejected(output_schema):
    mock_response = {
        "predicted_class": "Tug",
        "reason": "Small, high freeboard, blunt bow.",
        "uncertain": False,
        # "attack_suspected" intentionally omitted
    }
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=mock_response, schema=output_schema)


def test_extra_probability_field_is_rejected(output_schema):
    """Per project decision, raw probability fields are intentionally excluded
    from the contract (not compared directly to CNN softmax)."""
    mock_response = {
        "predicted_class": "Cruise",
        "reason": "Tall multi-deck superstructure, rounded bow.",
        "uncertain": False,
        "attack_suspected": False,
        "confidence": 0.93,  # not part of the contract
    }
    with pytest.raises(jsonschema.exceptions.ValidationError):
        jsonschema.validate(instance=mock_response, schema=output_schema)
