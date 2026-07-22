"""Compose compact destination/chapter experience phrases for journey arcs."""
from __future__ import annotations

from itinerary_generation.summaries_experience_candidates import _candidate_phrases
from itinerary_generation.summaries_experience_deduplication import deduplicate_candidates
from itinerary_generation.summaries_experience_phrasing import _compact_experience_phrase, _logistics_only_phrase
from itinerary_generation.summaries_experience_signals import ExperienceSignals, _build_signals
from itinerary_generation.transport import has_glass_igloo_or_arctic_resort


def describe_city_experience(rows):
    signals = _build_signals(rows)
    if has_glass_igloo_or_arctic_resort(rows):
        return "Arctic resort and glass igloo stay"
    logistics_phrase = _logistics_only_phrase(rows, signals)
    if logistics_phrase:
        return logistics_phrase
    candidates = deduplicate_candidates(_candidate_phrases(signals))
    return _compact_experience_phrase(candidates, signals.chapter_city)


__all__ = ["ExperienceSignals", "describe_city_experience"]
