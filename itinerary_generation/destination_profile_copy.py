"""Deterministic prose generation from destination profiles."""

from __future__ import annotations

import re
from typing import Iterable, Mapping, Sequence

from itinerary_generation.destination_profile_builder import destination_profile_for
from text_polish import polish_title


def _rows_text(rows: Iterable[Mapping[str, object]] | None) -> str:
    parts: list[str] = []
    for row in rows or []:
        if isinstance(row, Mapping):
            parts.extend(str(row.get(key, "") or "") for key in ("day", "city", "title", "original_title", "details", "description"))
    return " ".join(parts).lower()


from itinerary_generation.destination_copy_variants import stable_variant_index

def select_arrival_sentence(city: object, rows: Iterable[Mapping[str, object]] | None = None) -> str:
    profile = destination_profile_for(city)
    index = stable_variant_index(profile.name, _rows_text(rows), "arrival", count=len(profile.arrival_templates))
    return profile.arrival_templates[index].format(city=profile.name, identity=profile.arrival_identity)


def _format_focus(options: Sequence[str]) -> str:
    clean = list(dict.fromkeys(re.sub(r"\s+", " ", str(option or "").strip()) for option in options if str(option or "").strip()))
    if not clean: return "local streets, viewpoints, and the surrounding scenery"
    if len(clean) == 1: return clean[0]
    if len(clean) == 2: return f"{clean[0]} or {clean[1]}"
    return f"{clean[0]}, {clean[1]}, or {clean[2]}"


def destination_leisure_sentence(value: object, rows: Iterable[Mapping[str, object]] | None = None, options: Sequence[str] | None = None) -> str:
    profile = destination_profile_for(value)
    city = profile.name or polish_title(str(value or "").strip())
    if not city: return "Open time today is left flexible, with room to rest, explore independently, or settle into the day."
    context = _rows_text(rows)
    source = list(options or profile.atmosphere)
    offset = stable_variant_index(f"{city}|{context}|leisure", count=len(source)) if source else 0
    selected = (source[offset:] + source[:offset])[:3]
    template = profile.leisure_templates[stable_variant_index(city, context, "leisure-template", count=len(profile.leisure_templates))]
    return template.format(city=city, identity=profile.identity, focus=_format_focus(selected))


def _is_return_visit(visit_context: object | None) -> bool:
    return bool(getattr(visit_context, "is_return_visit", False))


def destination_arrival_intro(city: object, transfer_phrase: str, detail_level: str, *, display_destination: str | None = None, rows: Iterable[Mapping[str, object]] | None = None, visit_context: object | None = None) -> str:
    destination = str(display_destination or "").strip() or destination_profile_for(city).name or polish_title(str(city or "").strip()) or "this place"
    transfer_phrase = re.sub(r"\s+", " ", str(transfer_phrase or "").strip()) or "After arrival, follow the listed transfer arrangements."
    return_visit = _is_return_visit(visit_context)
    if detail_level == "Elegant concise": return f"{'Return to' if return_visit else 'Arrive in'} {destination}. {transfer_phrase}"
    if return_visit:
        profile = destination_profile_for(city); identity = profile.arrival_identity or profile.identity or destination
        arrival_sentence = f"Back in {identity}, the rest of the day is kept relaxed, with time to settle back into familiar surroundings."
    elif destination.casefold() != str(city or "").strip().casefold() and destination:
        arrival_sentence = f"After arrival, the rest of the day is yours to settle in and get oriented around {destination}."
    else: arrival_sentence = select_arrival_sentence(city, rows)
    return f"{'Return to' if return_visit else 'Arrive in'} {destination}. {transfer_phrase} {arrival_sentence}"


def destination_stay_intro(city: object, detail_level: str, rows: Iterable[Mapping[str, object]] | None = None, *, visit_context: object | None = None) -> str:
    destination = destination_profile_for(city).name or polish_title(str(city or "").strip()) or "this place"
    return_visit = _is_return_visit(visit_context)
    if detail_level == "Elegant concise":
        return f"{'Return to' if return_visit else 'Stay in'} {destination}. Time is kept flexible around the listed arrangements."
    if return_visit:
        profile = destination_profile_for(city); identity = profile.arrival_identity or profile.identity or destination
        return f"Return to {destination}. The day is kept flexible around the listed stay arrangements. Back in {identity}, any open time is yours to use at your own pace."
    return f"This is part of your stay in {destination}, with the day’s arrangements listed below. {select_arrival_sentence(city, rows)}"
