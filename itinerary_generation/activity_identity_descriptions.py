"""Description realization for canonical activity identities."""

from __future__ import annotations

import re
from typing import Mapping

from itinerary_generation.activity_identity_contract import ActivityIdentity
from itinerary_generation.nutshell_domain import resolve_nutshell_journey
from place_aliases import canonicalize_place_name
from text_polish import polish_client_text


def _source_text(row: Mapping[str, object]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in ("title", "original_title", "details", "raw")
    ) + " " + " ".join(str(item) for item in (row.get("includes") or ()))


def _icebreaker_name(identity: ActivityIdentity) -> str:
    title = identity.display_title or identity.source_title or "Icebreaker Cruise"
    title = re.sub(r"\bCruise\b", "", title, flags=re.IGNORECASE).strip(" -:|.,")
    return title or "Icebreaker"


def description_for_activity_identity(row: Mapping[str, object], identity: ActivityIdentity) -> str:
    """Return source-supported copy for identities requiring strict priority.

    An empty string means the general description composer may continue.  The
    rules here are deliberately limited to identity families where broad
    keyword fallbacks have historically produced false descriptions.
    """

    source = _source_text(row)
    lower = source.casefold()
    city = canonicalize_place_name(row.get("city", ""))
    place = f" in {city}" if city else ""
    family = identity.canonical_family.casefold()

    if family == "norway_in_a_nutshell" or identity.product_type == "scenic_route":
        journey = resolve_nutshell_journey(row)
        origin = journey.origin if journey else city
        destination = journey.destination if journey else ""
        route = (
            f" from {origin} to {destination}"
            if origin and destination
            else f" towards {destination}"
            if destination
            else ""
        )
        return polish_client_text(
            f"Follow the Norway in a Nutshell route{route}, with rail, coach and fjord-cruise segments arranged as one scenic journey."
        )

    if family == "northern_lights_activity" and (
        "ice floating" in lower
        or "frozen lake" in lower
        or ("floating" in lower and any(marker in lower for marker in ("thermal", "survival suit", "wetsuit")))
    ):
        return polish_client_text(
            f"Float in a frozen lake{place}, wearing a thermal survival suit while the Arctic night sky forms the setting for the experience."
        )

    if family.endswith("icebreaker_cruise") or identity.product_type == "icebreaker_cruise":
        product_name = _icebreaker_name(identity)
        return polish_client_text(
            f"Experience the {product_name}, with time on the frozen sea and the included ice-floating or sea-walk activities where listed."
        )

    if family in {"tromso_viewpoint_ticket_possible_fjellheisen", "tromso_viewpoint_ticket"}:
        return polish_client_text(
            "Use your pre-arranged ticket for a flexible viewpoint visit in Tromsø, with time to enjoy the surrounding views during the day."
        )

    if family == "tromso_kvaloya_sommaroy_fjord" and any(
        marker in lower for marker in ("photo", "photography", "camera settings", "minivan")
    ):
        return polish_client_text(
            f"Travel outside {city or 'Tromsø'} by minivan on a photo-focused excursion through Arctic landscapes, fjords and coastal scenery."
        )

    return ""


__all__ = ["description_for_activity_identity"]
