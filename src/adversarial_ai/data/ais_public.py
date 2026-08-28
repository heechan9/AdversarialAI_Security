"""Adapter for the MOF public AIS dynamic-information schema.

The adapter creates navigation context only. It must not be treated as an image
class label or as evidence for clean/adversarial model performance.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping


OFFICIAL_COLUMNS = (
    "MMSI",
    "수신시간",
    "경도",
    "위도",
    "SOG",
    "COG",
    "HEDING",
)
COORDINATE_SCALE_DIVISOR = 60000.0


@dataclass(frozen=True)
class AISNavigationContext:
    mmsi_masked: str
    received_at: str
    longitude_deg: float
    latitude_deg: float
    speed_over_ground: float
    course_over_ground_deg: float
    heading_deg: float
    source_dataset_id: str = "15129186"

    def to_dict(self) -> dict[str, str | float]:
        return asdict(self)


def _parse_timestamp(value: str) -> str:
    raw = value.strip()
    formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y%m%d%H%M%S",
    )
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw).isoformat()
    except ValueError as exc:
        raise ValueError(f"Invalid AIS reception timestamp: {value!r}") from exc


def _number(row: Mapping[str, str], column: str) -> float:
    try:
        return float(str(row[column]).strip())
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric AIS field {column}: {row.get(column)!r}") from exc


def parse_ais_row(row: Mapping[str, str]) -> AISNavigationContext:
    missing = [column for column in OFFICIAL_COLUMNS if column not in row]
    if missing:
        raise ValueError(f"Missing AIS columns: {missing}")

    longitude = _number(row, "경도") / COORDINATE_SCALE_DIVISOR
    latitude = _number(row, "위도") / COORDINATE_SCALE_DIVISOR
    sog = _number(row, "SOG")
    cog = _number(row, "COG")
    heading = _number(row, "HEDING")

    if not -180.0 <= longitude <= 180.0:
        raise ValueError(f"AIS longitude out of range after /60000: {longitude}")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError(f"AIS latitude out of range after /60000: {latitude}")
    if sog < 0:
        raise ValueError(f"AIS SOG must be non-negative: {sog}")
    if not 0.0 <= cog <= 360.0:
        raise ValueError(f"AIS COG out of range: {cog}")
    if not 0.0 <= heading <= 511.0:
        raise ValueError(f"AIS HEDING out of range: {heading}")

    return AISNavigationContext(
        mmsi_masked=str(row["MMSI"]).strip(),
        received_at=_parse_timestamp(str(row["수신시간"])),
        longitude_deg=longitude,
        latitude_deg=latitude,
        speed_over_ground=sog,
        course_over_ground_deg=cog,
        heading_deg=heading,
    )


def load_ais_csv(path: Path) -> list[AISNavigationContext]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(OFFICIAL_COLUMNS):
            raise ValueError(
                "Unexpected AIS schema: "
                f"expected {list(OFFICIAL_COLUMNS)}, got {reader.fieldnames}"
            )
        return [parse_ais_row(row) for row in reader]


def build_navigation_context(
    records: Iterable[AISNavigationContext],
) -> list[dict[str, str | float]]:
    """Return JSON-safe context for a future VLM/LLM or safety-simulation join."""
    return [record.to_dict() for record in records]
