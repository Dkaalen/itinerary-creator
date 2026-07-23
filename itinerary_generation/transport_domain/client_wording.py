"""Authoritative client-facing wording for one transport row.

Route extraction owns geographic truth. This module owns how those facts become
client copy for day headings, travel arrangements, inclusions and commercial
status. Consumers should not rebuild route phrases from supplier text.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from itinerary_generation.common_constants import TRANSPORT_TYPES
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from itinerary_generation.row_filters import get_commercial_status, get_row_type
from itinerary_generation.transport_detection import is_route_transfer
from itinerary_generation.transport_domain.routes import (
    TransportRouteFacts,
    _clean_route_place,
    _via_suffix,
    get_transport_route_facts,
)
from itinerary_generation.transport_model import get_transport_source_text, has_local_transfer_marker
from itinerary_generation.transport_safety import base_destination_from_terminal
from text_polish import polish_title


@dataclass(frozen=True)
class ClientTransportWording:
    """Prepared transport copy and the facts that justify it."""

    origin: str = ""
    destination: str = ""
    via: tuple[str, ...] = ()
    mode: str = ""
    service_label: str = ""
    arrangement_title: str = ""
    day_title: str = ""
    inclusion_title: str = ""
    commercial_status: str = "included"
    commercial_title: str = ""
    travel_phrase: str = ""

    @property
    def has_route(self) -> bool:
        return bool(self.destination)


def _route_phrase(label: str, facts: TransportRouteFacts) -> str:
    if facts.origin and facts.destination:
        return f"{label} from {facts.origin} to {facts.destination}{_via_suffix(facts.via)}"
    if facts.destination:
        return f"{label} to {facts.destination}"
    return label


def _train_label(source_lower: str) -> str:
    if "santa claus express" in source_lower:
        return "Santa Claus Express"
    if re.search(r"\b(?:overnight|night\s+train|sleeper|sleeping)\b", source_lower):
        return "Overnight Train Transfer"
    if re.search(r"\bday\s+train\b|\bintercity\s*\d+\b", source_lower):
        return "Train"
    return "Scenic Train Transfer"


def _coach_label(source_lower: str) -> str:
    if "panorama" in source_lower or "panoramic" in source_lower or "scenic" in source_lower:
        return "Panoramic Coach Transfer"
    if "long distance" in source_lower or "long-distance" in source_lower:
        return "Long-distance Coach Transfer"
    return "Coach Transfer"


def _cruise_label(row_type: str, source_lower: str) -> str:
    if row_type == "Ferry" or ("ferry" in source_lower and "cruise" not in source_lower):
        return "Ferry Transfer"
    if "overnight" in source_lower:
        return "Overnight Coastal Cruise"
    if "nærøyfjord" in source_lower or "naeroyfjord" in source_lower:
        return "Nærøyfjord Cruise"
    return "Coastal Cruise"


def _service_label(row_type: str, source_lower: str) -> str:
    if row_type == "Drive":
        return "Self-drive route"
    if row_type == "Flight" or "flight" in source_lower:
        return "Flight"
    if row_type == "Train" or "train" in source_lower:
        return _train_label(source_lower)
    if row_type in {"Coach", "Bus"} or re.search(r"\b(?:coach|bus)\b", source_lower):
        return _coach_label(source_lower)
    if row_type in {"Cruise", "Ferry"} or "cruise" in source_lower or "ferry" in source_lower:
        return _cruise_label(row_type, source_lower)
    if "shuttle" in source_lower:
        return "Shuttle transfer"
    if row_type == "Transfer" or "transfer" in source_lower:
        return "Private transfer" if "private" in source_lower else "Transfer"
    return polish_title(row_type or "Travel")


def _santa_claus_destination(source_text: str) -> str:
    match = re.search(
        r"\bsanta\s+claus\s+express\s+to\s+([A-Za-zÀ-ÿøØåÅäÄöÖ .'-]+?)"
        r"(?:\s+-\s+\d{1,2}:\d{2}|\s+-\s+Arrival|\s+\|\s+|\s+-\s+|$)",
        source_text,
        flags=re.IGNORECASE,
    )
    return _clean_route_place(match.group(1)) if match else ""


def _arrangement_title(row: dict, facts: TransportRouteFacts, label: str, source_text: str) -> str:
    row_type = get_row_type(row)
    lower = source_text.lower()

    if row_type == "Transfer" and has_local_transfer_marker(lower) and not is_route_transfer(row):
        return polish_title(row.get("title", "") or "Transfer")

    if label == "Santa Claus Express":
        santa_destination = _santa_claus_destination(source_text)
        if santa_destination:
            facts = TransportRouteFacts(destination=santa_destination, mode=facts.mode, confidence=facts.confidence)

    if row_type == "Cruise" and "arrival" in lower and "overnight" not in lower:
        return f"Cruise arrival to {facts.destination}" if facts.destination else "Cruise arrival"

    if "geiranger fjord cruise" in lower or "geirangerfjord" in lower:
        if facts.destination and facts.destination.casefold() == "geiranger":
            return (
                "Geirangerfjord Cruise from Ålesund to Geiranger"
                if facts.origin
                else "One-way Geirangerfjord Cruise to Geiranger"
            )

    title = _route_phrase(label, facts)
    if row_type in {"Cruise", "Ferry"} or "cruise" in lower or "ferry" in lower:
        ship_match = re.search(r"\bonboard\s+([^|,;]+?)(?:\s+-\s+|\s+\||,|;|$)", source_text, flags=re.IGNORECASE)
        if ship_match:
            ship = polish_title(ship_match.group(1).strip(" .-:|"))
            if ship and ship.casefold() not in title.casefold():
                title += f" onboard {ship}"
    return title or polish_title(row.get("title", "") or "Travel")


def _day_title(row: dict, facts: TransportRouteFacts, arrangement_title: str, label: str, source_lower: str) -> str:
    destination = polish_title(base_destination_from_terminal(facts.destination) or facts.destination)
    if not destination:
        return polish_title(arrangement_title)
    if get_row_type(row) == "Drive" or "self-drive" in source_lower:
        destination = re.split(r"\s+via\s+", destination, maxsplit=1, flags=re.IGNORECASE)[0].strip()
        return f"Drive to {destination}"
    if label == "Flight":
        return f"Flight to {destination}"
    if "Train" in label:
        if label == "Santa Claus Express":
            return f"Santa Claus Express to {destination}"
        return f"Overnight train to {destination}" if label.startswith("Overnight") else f"Train to {destination}"
    if "Coach" in label:
        return f"Coach Transfer to {destination}"
    if label in {"Transfer", "Private transfer", "Shuttle transfer"}:
        return f"Transfer to {destination}"
    if label == "Ferry Transfer":
        return f"Ferry to {destination}"
    if "Cruise" in label or "cruise" in source_lower:
        if "arrival" in source_lower:
            return f"Arrival in {destination}" if row.get("is_render_only") else f"Cruise arrival to {destination}"
        return f"Cruise to {destination}"
    return polish_title(arrangement_title)



def _travel_phrase(facts: TransportRouteFacts, mode: str, source_lower: str) -> str:
    mode_label = {
        "train": "by rail",
        "coach": "by coach",
        "ferry": "by ferry",
        "cruise": "by cruise",
        "flight": "by flight",
        "drive": "by road",
        "self_drive": "by road",
    }.get(mode, "")
    overnight = bool(re.search(r"\b(?:overnight|night\s+train|sleeper|sleeping)\b", source_lower))
    verb = "Travel overnight" if overnight else "Travel"
    if facts.origin and facts.destination:
        phrase = f"{verb} from {facts.origin} to {facts.destination}"
    elif facts.destination:
        phrase = f"Continue to {facts.destination}"
    else:
        return ""
    if mode_label:
        phrase += f" {mode_label}"
    if facts.via:
        phrase += _via_suffix(facts.via)
    return phrase

def _commercial_title(arrangement_title: str, status: str, mode: str) -> str:
    if status != "self_arranged":
        return arrangement_title
    clean = arrangement_title.strip()
    if not clean:
        return "Self-arranged travel (not included)"
    if mode == "flight":
        return f"Self-arranged {clean[0].lower() + clean[1:]} (not included)"
    return f"{clean} (self-arranged, not included)"


def build_client_transport_wording(row: dict) -> ClientTransportWording:
    """Return the single client-copy contract for one transport row."""

    source_text = get_transport_source_text(row)
    source_lower = source_text.lower()
    facts = get_transport_route_facts(row)
    journey = resolve_nutshell_journey(row)
    status = get_commercial_status(row)

    if journey is not None:
        arrangement = journey.client_title
        destination = journey.destination or facts.destination
        day_title = f"Norway in a Nutshell to {destination}" if destination else arrangement
        return ClientTransportWording(
            origin=journey.origin or facts.origin,
            destination=destination,
            via=tuple(journey.route_points[1:-1]) if len(journey.route_points) > 2 else facts.via,
            mode="nutshell",
            service_label="Norway in a Nutshell",
            arrangement_title=arrangement,
            day_title=day_title,
            inclusion_title=arrangement,
            commercial_status=status,
            commercial_title=_commercial_title(arrangement, status, "nutshell"),
            travel_phrase=(
                f"Follow the Norway in a Nutshell route from {journey.origin} to {destination}"
                if journey.origin and destination
                else f"Follow the Norway in a Nutshell route towards {destination}" if destination else arrangement
            ),
        )

    label = _service_label(get_row_type(row), source_lower)
    arrangement = _arrangement_title(row, facts, label, source_text)
    day_title = _day_title(row, facts, arrangement, label, source_lower)
    return ClientTransportWording(
        origin=facts.origin,
        destination=facts.destination,
        via=facts.via,
        mode=facts.mode,
        service_label=label,
        arrangement_title=arrangement,
        day_title=day_title,
        inclusion_title=arrangement,
        commercial_status=status,
        commercial_title=_commercial_title(arrangement, status, facts.mode),
        travel_phrase=_travel_phrase(facts, facts.mode, source_lower),
    )


def build_day_client_transport_wording(day_rows) -> ClientTransportWording | None:
    """Return client wording for the primary route row of one day.

    Product and route selection belongs beside the wording authority so intro,
    title and detail consumers cannot select different transport rows.
    """

    candidates = []
    for source_row in day_rows:
        row = dict(source_row)
        row_type = get_row_type(row)
        if row_type not in TRANSPORT_TYPES and row_type not in {"Transfer", "Drive"} and not is_route_transfer(row):
            continue
        source_lower = get_transport_source_text(row).casefold()
        if row_type == "Transfer" and has_local_transfer_marker(source_lower) and not is_route_transfer(row):
            # Local airport/station/hotel logistics support an arrival or
            # departure day; they do not own the day-level route narrative.
            continue
        candidates.append(row)
    if not candidates:
        return None

    for row in candidates:
        if resolve_nutshell_journey(row) is not None:
            return build_client_transport_wording(row)
    for row in candidates:
        source = get_transport_source_text(row).casefold()
        if "coastal" in source and "cruise" in source:
            return build_client_transport_wording(row)
    for row in candidates:
        if get_row_type(row) == "Transfer":
            continue
        wording = build_client_transport_wording(row)
        if wording.origin and wording.destination:
            return wording
    for row in candidates:
        if get_row_type(row) in TRANSPORT_TYPES:
            return build_client_transport_wording(row)
    return build_client_transport_wording(candidates[0])


__all__ = ["ClientTransportWording", "build_client_transport_wording", "build_day_client_transport_wording"]
