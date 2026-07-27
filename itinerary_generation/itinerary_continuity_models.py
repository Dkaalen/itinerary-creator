"""Immutable public models for canonical itinerary continuity."""

from __future__ import annotations

from dataclasses import dataclass

from shared.text import clean_space

ERROR = "error"
WARNING = "warning"


@dataclass(frozen=True)
class ContinuityFinding:
    """One immutable continuity problem linked to its source rows."""

    severity: str
    code: str
    message: str
    context: str = ""
    source_row_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DayContinuityState:
    """Canonical itinerary-level geographic and temporal state for one day."""

    day: str
    source_row_ids: tuple[str, ...] = ()
    start_place: str = ""
    end_place: str = ""
    overnight_place: str = ""
    chapter_city: str = ""
    visit_number: int = 1
    previous_visit_days: tuple[str, ...] = ()
    transit_cities: tuple[str, ...] = ()
    completed_visit: bool = False
    transit_only: bool = False
    chapter_start: bool = False
    chapter_continuation: bool = False
    return_visit: bool = False
    day_trip_return: bool = False
    explicit_arrival: bool = False
    destination_arrival: bool = False
    arrival_stay: bool = False
    welcome_allowed: bool = False
    same_city_accommodation_change: bool = False
    stay_continuation: bool = False
    previous_overnight_place: str = ""


@dataclass(frozen=True)
class ItineraryContinuityReport:
    """Immutable findings and per-day continuity decisions for one itinerary."""

    findings: tuple[ContinuityFinding, ...] = ()
    days: tuple[DayContinuityState, ...] = ()

    def day_state(self, day: object) -> DayContinuityState | None:
        label = clean_space(day)
        return next((item for item in self.days if item.day == label), None)

    def day_map(self) -> dict[str, DayContinuityState]:
        return {item.day: item for item in self.days}


__all__ = [
    "ERROR",
    "WARNING",
    "ContinuityFinding",
    "DayContinuityState",
    "ItineraryContinuityReport",
]
