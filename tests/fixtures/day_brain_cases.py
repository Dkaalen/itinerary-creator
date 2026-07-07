"""Small itinerary fixtures for day-brain copy audits and regressions."""

from __future__ import annotations

from itinerary_generation.copy.visit_context import DayVisitContext
from itinerary_generation.day_copy_audit import DayCopyAuditCase


def _row(day: str, row_type: str, city: str, title: str, details: str = "") -> dict:
    return {
        "day": day,
        "type": row_type,
        "effective_type": row_type,
        "city": city,
        "title": title,
        "details": details,
        "row_id": f"{day}-{row_type}-{abs(hash((day, row_type, city, title))) % 100000}",
    }


ARRIVAL_ONWARD_ROWS = (
    _row("Day 1", "Arrival", "Helsinki", "Arrival in Helsinki"),
    _row("Day 1", "Transfer", "Helsinki", "Private transfer from Helsinki Airport to Helsinki Central Station"),
    _row("Day 1", "Train", "Rovaniemi", "Santa Claus Express Helsinki to Rovaniemi - overnight train"),
)

SAME_CITY_ACCOMMODATION_CHANGE_ROWS = (
    _row("Day 4", "Transfer", "Rovaniemi", "Private transfer from your hotel to your next accommodation"),
    _row("Day 4", "Hotel", "Rovaniemi", "Glass igloo stay in Rovaniemi", "1 night in a glass cabin"),
)

RETURN_VISIT_ROWS = (
    _row("Day 7", "Train", "Kiruna", "Train Abisko to Kiruna"),
    _row("Day 7", "Hotel", "Kiruna", "Hotel stay in Kiruna"),
)

FULL_LEISURE_ROWS = (
    _row("Day 5", "Leisure", "Rovaniemi", "A day at leisure in Rovaniemi"),
)

TRAVEL_HEAVY_ROWS = (
    _row("Day 6", "Transfer", "Rovaniemi", "Private transfer from hotel to Rovaniemi railway station"),
    _row("Day 6", "Train", "Helsinki", "Train Rovaniemi to Helsinki"),
    _row("Day 6", "Transfer", "Helsinki", "Private transfer from Helsinki Central Station to harbour"),
    _row("Day 6", "Cruise", "Stockholm", "Overnight cruise Helsinki to Stockholm"),
    _row("Day 6", "Leisure", "Stockholm", "Spend time at leisure onboard the cruise"),
)

CRUISE_ONBOARD_ROWS = (
    _row("Day 8", "Cruise", "Cruise", "Spend time at leisure onboard the coastal cruise"),
)

DAY_BRAIN_AUDIT_CASES = (
    DayCopyAuditCase(
        "arrival-onward",
        "Arrival city is only a transit point before onward overnight train.",
        ARRIVAL_ONWARD_ROWS,
        expected_intent="arrival_onward_travel",
        legacy_risk="Could welcome the guest to Helsinki or invent Helsinki accommodation.",
    ),
    DayCopyAuditCase(
        "same-city-accommodation-change",
        "Move from one Rovaniemi stay to another without re-welcoming the city.",
        SAME_CITY_ACCOMMODATION_CHANGE_ROWS,
        expected_intent="same_city_accommodation_change",
        legacy_risk="Could welcome the guest to Rovaniemi again.",
    ),
    DayCopyAuditCase(
        "return-visit",
        "Return to Kiruna after an earlier visit.",
        RETURN_VISIT_ROWS,
        expected_intent="return_visit",
        legacy_risk="Could say Welcome to Kiruna or first impressions.",
        visit_context=DayVisitContext(day="Day 7", city="Kiruna", canonical_city="Kiruna", visit_number=2, previous_days=("Day 2",)),
    ),
    DayCopyAuditCase(
        "full-leisure",
        "Full leisure day should not be called remaining time.",
        FULL_LEISURE_ROWS,
        expected_intent="full_leisure_day",
        legacy_risk="Could describe a full day as remaining time.",
    ),
    DayCopyAuditCase(
        "travel-heavy",
        "Long logistics day should be cautious about free time.",
        TRAVEL_HEAVY_ROWS,
        expected_intent="overnight_transport_day",
        legacy_risk="Could imply generous free time despite multiple travel legs.",
    ),
    DayCopyAuditCase(
        "cruise-onboard",
        "Onboard leisure should be natural and not repetitive filler.",
        CRUISE_ONBOARD_ROWS,
        expected_intent="cruise_day",
        legacy_risk="Could repeat generic leisure filler.",
    ),
)


__all__ = [
    "ARRIVAL_ONWARD_ROWS",
    "CRUISE_ONBOARD_ROWS",
    "DAY_BRAIN_AUDIT_CASES",
    "FULL_LEISURE_ROWS",
    "RETURN_VISIT_ROWS",
    "SAME_CITY_ACCOMMODATION_CHANGE_ROWS",
    "TRAVEL_HEAVY_ROWS",
]
