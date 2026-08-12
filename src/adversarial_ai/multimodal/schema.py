"""Phase 1 perception schema for the OpenAI ship-classification PoC.

This is the "perception" schema only -- classification, self-reported
confidence, and an attack-suspicion flag. Safety-action fields
(situation description, recommended action) belong to a separate Phase 2
schema and must not be added here.
"""

from __future__ import annotations

PERCEPTION_SCHEMA = {
    "type": "object",
    "properties": {
        "predicted_class": {
            "type": "string",
            "enum": [
                "Aircraft Carrier",
                "Bulkers",
                "Car Carrier",
                "Container Ship",
                "Cruise",
                "DDG",
                "Recreational",
                "Sailboat",
                "Submarine",
                "Tug",
            ],
        },
        "reason": {"type": "string"},
        "uncertain": {"type": "boolean"},
        "attack_suspected": {"type": "boolean"},
        "self_reported_confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
        },
    },
    "required": [
        "predicted_class",
        "reason",
        "uncertain",
        "attack_suspected",
        "self_reported_confidence",
    ],
    "additionalProperties": False,
}

SHIP_CLASSES: tuple[str, ...] = tuple(
    PERCEPTION_SCHEMA["properties"]["predicted_class"]["enum"]
)

# self_reported_confidence is the model's own self-assessment score, not a
# statistically calibrated probability. It must not be treated as one when
# analyzing results (e.g. do not compute calibration curves against it
# without noting this caveat).
CONFIDENCE_CAVEAT = (
    "self_reported_confidence is the model's own self-assessment, not a "
    "calibrated probability."
)
