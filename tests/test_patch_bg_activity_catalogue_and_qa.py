from __future__ import annotations

from itinerary_generation.activity_training_catalogue import (
    activity_training_entries,
    validate_activity_training_catalogue,
)
from itinerary_generation.common import group_rows_by_day
from itinerary_generation.qa_report import build_qa_report
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_parser import parse_itinerary
from normalizer import normalize_itinerary_rows


def test_activity_training_catalogue_schema_is_valid() -> None:
    assert validate_activity_training_catalogue() == ()
    assert len(activity_training_entries()) >= 80


def test_low_confidence_activity_structure_reaches_qa_report() -> None:
    raw = """
Day 1	Activity	01/01/2027								Tromso	Mystery Arctic Evening Experience | 8 PM | 3 Hrs | Pick up / meeting point Tromsø Havn Prostneset Terminal | What's included? Local guide Hot drinks Winter clothing
"""
    rows = normalize_itinerary_rows(parse_itinerary(raw))
    document = build_itinerary_document(rows, group_rows_by_day(rows))
    report = build_qa_report(rows, {}, warnings=document.warnings)

    assert any(w.code == "low_confidence_activity_structure" for w in document.warnings)
    assert any(w.code == "low_confidence_activity_structure" for w in report.warnings)
