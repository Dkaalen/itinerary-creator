"""Canonical destination lookup and deterministic fallback order."""
from __future__ import annotations

from dataclasses import dataclass

from itinerary_generation.destination_registry import NordicDestination, destination_for_alias
from text_polish import polish_title


@dataclass(frozen=True)
class ResolvedDestination:
    requested: str
    name: str
    record: NordicDestination | None
    source: str


def resolve_destination(value: object) -> ResolvedDestination:
    requested = str(value or "").strip()
    direct = destination_for_alias(value)
    if direct is not None:
        return ResolvedDestination(requested, direct.name, direct, "direct_alias")
    polished = polish_title(requested)
    record = destination_for_alias(polished) if polished else None
    if record is not None:
        return ResolvedDestination(requested, record.name, record, "polished_alias")
    return ResolvedDestination(requested, polished, None, "polished_unknown")


def record_for(value: object) -> NordicDestination | None:
    return resolve_destination(value).record


def display_name(value: object, record: NordicDestination | None = None) -> str:
    if record is not None:
        return record.name
    return resolve_destination(value).name
