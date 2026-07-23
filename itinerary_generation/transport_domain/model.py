"""Typed transport-domain summaries.\n\nThe app still accepts loose parser row dictionaries, but transport rendering,\ninclusions and exclusions should derive from one normalized view.  This module\nkeeps that view small and UI-neutral so legacy callers can migrate without\npassing generated HTML around as state.\n"""

from __future__ import annotations

from dataclasses import dataclass, field

from itinerary_generation.common import get_row_type, is_self_arranged
from itinerary_generation.transport_model import get_transport_source_text, is_transport_like_row
from itinerary_generation.transport_domain.client_wording import build_client_transport_wording


@dataclass(frozen=True)
class TransportRoute:
    """Normalized origin/destination/via route details for a transport row."""

    origin: str = ""
    destination: str = ""
    via: tuple[str, ...] = field(default_factory=tuple)
    phrase: str = ""

    @property
    def has_route(self) -> bool:
        return bool(self.destination or self.phrase)


@dataclass(frozen=True)
class TransportSummary:
    """Canonical transport-domain interpretation of one itinerary row."""

    row_type: str
    source_text: str
    route: TransportRoute
    client_title: str
    transfer_title: str
    is_transport_like: bool
    is_self_arranged: bool
    is_route_transfer: bool
    is_cruise_leisure: bool


def build_transport_summary(row: dict, *, include_drive: bool = False) -> TransportSummary:
    """Return one reusable transport interpretation for a row dictionary."""

    row_type = get_row_type(row)
    source_text = get_transport_source_text(row)
    wording = build_client_transport_wording(row)
    route_phrase = wording.arrangement_title
    transfer_title = wording.arrangement_title
    from itinerary_generation.transport_detection import is_route_transfer

    is_cruise_leisure = (
        row_type == "Cruise"
        and "leisure" in source_text.lower()
        and "cruise" in source_text.lower()
    )
    return TransportSummary(
        row_type=row_type,
        source_text=source_text,
        route=TransportRoute(origin=wording.origin, destination=wording.destination, via=wording.via, phrase=route_phrase),
        client_title=route_phrase or transfer_title or str(row.get("title") or ""),
        transfer_title=transfer_title,
        is_transport_like=is_transport_like_row(row, include_drive=include_drive),
        is_self_arranged=is_self_arranged(row),
        is_route_transfer=is_route_transfer(row),
        is_cruise_leisure=is_cruise_leisure,
    )
