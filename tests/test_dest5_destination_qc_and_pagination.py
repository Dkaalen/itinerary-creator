from __future__ import annotations

from itinerary_generation.itinerary_health_checks import build_itinerary_health_issues
from ui.inclusion_pages import paginate_categorized_inclusions


def _detail_items(count: int, prefix: str) -> list[dict[str, object]]:
    return [
        {
            "label": f"{prefix} service {index}",
            "detail_lines": [
                "Confirmed supplier arrangement with client-facing details.",
                "Final timing will be reconfirmed in the travel documents.",
            ],
        }
        for index in range(1, count + 1)
    ]


def test_destination_qc_flags_unknown_registry_place_without_flagging_known_terminals():
    rows = [
        {
            "day": "Day 1",
            "type": "Transfer",
            "effective_type": "Transfer",
            "city": "Bergen",
            "title": "Self transfer to Bergen Train Station",
            "details": "Bergen: Self transfer to Bergen Train Station",
        },
        {
            "day": "Day 2",
            "type": "Activity",
            "effective_type": "Activity",
            "city": "Atlantis Harbor",
            "title": "Guided harbour walk",
            "details": "Atlantis Harbor: Guided harbour walk",
        },
    ]

    issues = build_itinerary_health_issues(rows)
    unknown = [issue for issue in issues if issue.code == "unknown_destination"]

    assert len(unknown) == 1
    assert "Atlantis" in unknown[0].message
    assert "Bergen Train Station" not in "\n".join(issue.message for issue in issues)


def test_inclusion_pagination_keeps_private_transfers_off_page_bottom():
    sections = [
        {"title": "Rail journeys", "items": _detail_items(13, "Rail")},
        {"title": "Private transfers", "items": _detail_items(2, "Private transfer")},
        {"title": "Ferries & Cruises", "items": _detail_items(1, "Cruise")},
    ]

    pages = paginate_categorized_inclusions(sections)

    assert len(pages) >= 2
    assert [section["title"] for section in pages[0]] == ["Rail journeys"]
    assert pages[1][0]["title"] == "Private transfers"


def test_inclusion_pagination_keeps_ferries_and_cruises_off_page_bottom():
    sections = [
        {"title": "Accommodation", "items": _detail_items(12, "Hotel")},
        {"title": "Ferries & Cruises", "items": _detail_items(2, "Cruise")},
    ]

    pages = paginate_categorized_inclusions(sections)

    assert len(pages) >= 2
    assert [section["title"] for section in pages[0]] == ["Accommodation"]
    assert pages[1][0]["title"] == "Ferries & Cruises"
