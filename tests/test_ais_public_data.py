import csv
from pathlib import Path

import pytest

from adversarial_ai.data.ais_public import (
    OFFICIAL_COLUMNS,
    build_navigation_context,
    load_ais_csv,
    parse_ais_row,
)


VALID_ROW = {
    "MMSI": "***",
    "수신시간": "2022-01-01 12:34:56",
    "경도": "7758000",
    "위도": "2130000",
    "SOG": "12.5",
    "COG": "181.2",
    "HEDING": "180",
}


def test_parse_official_ais_schema_and_coordinate_scale():
    record = parse_ais_row(VALID_ROW)

    assert record.mmsi_masked == "***"
    assert record.longitude_deg == pytest.approx(129.3)
    assert record.latitude_deg == pytest.approx(35.5)
    assert record.speed_over_ground == 12.5
    assert record.received_at == "2022-01-01T12:34:56"


def test_missing_official_column_is_rejected():
    row = dict(VALID_ROW)
    row.pop("HEDING")

    with pytest.raises(ValueError, match="Missing AIS columns"):
        parse_ais_row(row)


def test_out_of_range_coordinate_is_rejected():
    row = dict(VALID_ROW)
    row["위도"] = str(91 * 60000)

    with pytest.raises(ValueError, match="latitude out of range"):
        parse_ais_row(row)


def test_csv_loader_requires_exact_official_column_order(tmp_path: Path):
    path = tmp_path / "ais.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(OFFICIAL_COLUMNS))
        writer.writeheader()
        writer.writerow(VALID_ROW)

    records = load_ais_csv(path)
    context = build_navigation_context(records)

    assert len(context) == 1
    assert context[0]["source_dataset_id"] == "15129186"
    assert context[0]["course_over_ground_deg"] == 181.2
