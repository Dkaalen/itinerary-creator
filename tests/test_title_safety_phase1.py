import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from itinerary_generation.canonical_builder import canonical_activity_block


def test_canonical_activity_title_never_falls_back_to_raw_supplier_title():
    row = {
        "row_id": "unsafe-title",
        "type": "Activity",
        "effective_type": "Activity",
        "title": "Opening Hours: 10:00-18:00 | Includese: Tickets only",
        "original_title": "Opening Hours: 10:00-18:00 | Includese: Tickets only",
        "details": "Opening Hours: 10:00-18:00 | Includese: Tickets only",
        "includes": [],
    }

    block = canonical_activity_block(row)

    assert block.title == "Experience"
    assert "Opening Hours" not in block.title
    assert "Includese" not in block.title
    assert "|" not in block.title


def test_canonical_activity_title_has_safe_fallback_after_cleaning():
    row = {
        "row_id": "voucher-title",
        "type": "Activity",
        "effective_type": "Activity",
        "title": "Final timing to be shared in voucher",
        "original_title": "Final timing to be shared in voucher",
        "details": "Final timing to be shared in voucher",
        "includes": [],
    }

    block = canonical_activity_block(row)

    assert block.title == "Experience"
    assert "voucher" not in block.title.lower()
    assert "timing" not in block.title.lower()


def test_canonical_activity_includes_are_deduplicated_before_rendering():
    row = {
        "row_id": "duplicate-includes",
        "type": "Activity",
        "effective_type": "Activity",
        "title": "Museum Visit",
        "original_title": "Museum Visit",
        "details": "Museum Visit",
        "includes": ["Admission ticket", "Admission ticket", "Local guide", "Local guide"],
    }

    block = canonical_activity_block(row)

    assert block.includes.count("Admission ticket") == 1
    assert block.includes.count("Local guide") == 1
