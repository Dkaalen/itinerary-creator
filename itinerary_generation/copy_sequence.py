"""Deterministic itinerary-level copy variation.

Day writers remain responsible for factual wording.  This module only varies
approved generic templates after all days have been assembled, so repetition is
handled with itinerary context without mutating source rows or manual editor
copy.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from itinerary_generation.render_model import RenderBlock, RenderDay, RenderDocument

_GENERIC_INTRO_SOURCES = {
    "full_leisure_intro",
    "partial_leisure_intro",
    "admin_fallback_intro",
    "contextual_day_intro",
    "arrival_stay_intro",
}
_STRONG_PRODUCT_MARKERS = (
    "overnight", "lavvo", "glass igloo", "lysefjord", "preikestolen",
    "whale", "reindeer", "husky", "snowmobile", "icebreaker", "blue lagoon",
    "golden circle", "vasa", "tivoli", "norway in a nutshell",
)
_NORTHERN_LIGHTS_RE = re.compile(r"\b(?:northern lights|aurora)\b", re.IGNORECASE)


def _norm(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _manual_day(day: RenderDay) -> bool:
    labels = day.labels or {}
    if str(labels.get("intro_manual_override", "")).casefold() == "true":
        return True
    return any(block.kind == "manual_day_html" for block in day.blocks or [])


def _activity_title(day: RenderDay) -> str:
    for block in day.blocks or []:
        if block.kind in {"activity", "optional_experience"} and str(block.title or "").strip():
            return str(block.title).strip()
    return "the included Northern Lights experience"


def _has_strong_product_copy(day: RenderDay) -> bool:
    text = " ".join(
        [day.title, day.intro]
        + [f"{block.title} {block.description}" for block in day.blocks or []]
    ).casefold()
    return any(marker in text for marker in _STRONG_PRODUCT_MARKERS)


def _leisure_variant(city: str, occurrence: int) -> str:
    place = city or "the area"
    options = (
        f"Use the open time in {place} at your own pace, whether for a local walk, a relaxed meal or a quieter pause.",
        f"The schedule stays open in {place}, leaving room for independent plans without adding pressure to the day.",
        f"Keep this free time in {place} flexible around your own interests and energy level.",
        f"No additional arrangements are fixed for this time in {place}, so you can explore locally or simply slow the pace.",
        f"This open period in {place} is yours to shape, with no need to overfill the itinerary.",
        f"Enjoy an unhurried stretch of independent time in {place}, close to the day’s confirmed arrangements.",
    )
    return options[(occurrence - 1) % len(options)]


def _arrival_variant(city: str, occurrence: int) -> str:
    place = city or "the destination"
    options = (
        f"Arrive in {place} and settle into the next part of your journey.",
        f"Your journey reaches {place}, where the next destination chapter begins.",
        f"After arriving in {place}, take time to settle in before the itinerary continues.",
        f"The trip now moves into {place}, with the confirmed arrival arrangements set out below.",
    )
    return options[(occurrence - 1) % len(options)]


def _northern_lights_variant(day: RenderDay, occurrence: int) -> str:
    title = _activity_title(day)
    city = day.city or "the area"
    options = (
        f"This evening, join {title} in {city} and head out in search of the Northern Lights, subject to weather and natural conditions.",
        f"Later today, {title} takes you away from the brighter city lights for another weather-dependent Northern Lights search.",
        f"The evening is reserved for {title}, with the route chosen according to conditions and sightings never guaranteed.",
    )
    return options[(occurrence - 1) % len(options)]


@dataclass(slots=True)
class CopySequencePlan:
    intro_occurrences: Counter[str] = field(default_factory=Counter)
    leisure_occurrences: Counter[str] = field(default_factory=Counter)
    arrival_occurrence: int = 0
    northern_lights_occurrence: int = 0

    def apply_day(self, day: RenderDay) -> None:
        if _manual_day(day):
            return
        source = str((day.labels or {}).get("intro_decision_source", ""))
        intro_key = _norm(day.intro)
        self.intro_occurrences[intro_key] += 1
        intro_occurrence = self.intro_occurrences[intro_key]

        if source == "arrival_stay_intro":
            self.arrival_occurrence += 1
            if self.arrival_occurrence > 1 and intro_occurrence > 1:
                day.intro = _arrival_variant(day.city, self.arrival_occurrence)
        elif (
            source == "activity_day_intro"
            and _NORTHERN_LIGHTS_RE.search(" ".join([day.title, day.intro, _activity_title(day)]))
            and not _has_strong_product_copy(day)
        ):
            self.northern_lights_occurrence += 1
            if self.northern_lights_occurrence > 1:
                day.intro = _northern_lights_variant(day, self.northern_lights_occurrence)
        elif source in _GENERIC_INTRO_SOURCES and intro_occurrence > 1:
            # Repeated generic intro: use the same fact boundary as the leisure
            # channel rather than inventing a new product description.
            day.intro = _leisure_variant(day.city, intro_occurrence)

        for block in day.blocks or []:
            if block.kind not in {"leisure", "cruise_leisure"}:
                continue
            key = _norm(block.description)
            self.leisure_occurrences[key] += 1
            occurrence = self.leisure_occurrences[key]
            if occurrence > 1:
                block.description = _leisure_variant(day.city, occurrence)


def apply_copy_sequence_plan(render_document: RenderDocument) -> RenderDocument:
    """Apply deterministic itinerary-level variation to approved generic copy."""

    plan = CopySequencePlan()
    for day in render_document.days or []:
        plan.apply_day(day)
    return render_document


__all__ = ["CopySequencePlan", "apply_copy_sequence_plan"]
