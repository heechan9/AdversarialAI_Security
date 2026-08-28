from pathlib import Path

from adversarial_ai.data.vts_public import validate_uploaded_vts_data


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "public"


def test_uploaded_vts_assets_are_exact_and_separate() -> None:
    summary = validate_uploaded_vts_data(
        DATA / "관제기반_선박운항정보.csv",
        DATA / "선박위치정보.csv",
        expected_voyage_sha256="213c6cf3b475d7395e25acd51b9cca78fa939166f91de57b2ee2976fb580f172",
        expected_position_sha256="21c51de49951ac92b2b6d5ffe034e9cdfeb947a0bbcf615e25fbaee6b76d784e",
    )

    assert summary["voyage_records"] == 522
    assert summary["position_records"] == 528
    assert summary["callsign_intersection_count"] == 0
    assert summary["join_allowed"] is False
    assert summary["voyage_event_counts"] == {
        "입항": 115, "출항": 115, "이안": 81, "양묘": 65,
        "접안": 65, "이선": 61, "투묘": 20,
    }
    assert summary["navigation_status_counts"]["항해(동력)"] == 207
    assert summary["navigation_status_counts"][""] == 203
