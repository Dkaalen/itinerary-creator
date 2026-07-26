from __future__ import annotations

from pathlib import Path

from itinerary_generation.activity_products import fingerprint_activity


ROOT = Path(__file__).resolve().parents[1]


def test_activity_products_uses_neutral_domain_owners() -> None:
    facade = ROOT / "itinerary_generation" / "activity_products.py"
    assert len(facade.read_text(encoding="utf-8").splitlines()) < 140

    assert (ROOT / "itinerary_domain" / "activity_product_core.py").exists()
    assert (ROOT / "itinerary_domain" / "activity_product_text.py").exists()
    assert (ROOT / "itinerary_domain" / "activity_product_rules" / "norway.py").exists()
    assert (ROOT / "itinerary_domain" / "activity_product_rules" / "nordic.py").exists()
    assert (ROOT / "itinerary_domain" / "activity_product_rules" / "iceland.py").exists()
    assert (ROOT / "itinerary_domain" / "activity_product_rules" / "scandinavia.py").exists()

    assert not (ROOT / "itinerary_generation" / "activity_product_core.py").exists()
    assert not (ROOT / "itinerary_generation" / "activity_product_text.py").exists()
    assert not (ROOT / "itinerary_generation" / "activity_product_rules").exists()


def test_split_activity_product_matchers_preserve_public_api() -> None:
    examples = [
        (
            {"city": "Tromso", "title": "Tromsø: Northern Lights Safari to Aurora Basecamp | 18:15 | 7 Hrs"},
            "Northern Lights Safari to Aurora Basecamp",
        ),
        (
            {"city": "Bergen", "title": "Norway in a NUtshell | Bergen to Oslo |08:30 - 22:30"},
            "Norway in a Nutshell from Bergen to Oslo",
        ),
        (
            {"city": "Helsinki", "title": "Helsinki: City Highlights & Suomenlinna Day Tour | 10 AM | 5 Hrs"},
            "Helsinki City Highlights & Suomenlinna Day Tour",
        ),
        (
            {"city": "Reykjavik", "title": "Reykjavík: Golden Circle & Blue Lagoon Tour (Entrance Fees Included) |9 AM | 11 Hrs"},
            "Blue Lagoon Admission",
        ),
    ]

    for row, expected_title in examples:
        fingerprint = fingerprint_activity(row)
        assert fingerprint is not None
        assert fingerprint.display_title == expected_title
