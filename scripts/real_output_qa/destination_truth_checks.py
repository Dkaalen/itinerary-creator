"""Destination/currency truth checks for rendered output QA."""

from __future__ import annotations

import re
from typing import Sequence

from scripts.real_output_qa.models import OutputTextIssue, TextSegment
from scripts.real_output_qa.rules import AIRPORT_STAY_RE, CURRENCY_CODES, ROUTE_FALSE_PLACE_RE
from scripts.real_output_qa.text_utils import add_issue as _add_issue, clean_text as _clean_text


def score_city_currency_safety(
    issues: list[OutputTextIssue],
    segments: Sequence[TextSegment],
    route_text: object,
) -> None:
    route_parts = {
        part.strip().upper()
        for part in re.split(r"[·,>\-/]+", _clean_text(route_text))
        if part.strip()
    }
    for code in sorted(route_parts & CURRENCY_CODES):
        _add_issue(
            issues,
            "currency_code_used_as_city",
            "error",
            "Currency code appears in route/destination line.",
            location="cover.route",
            excerpt=code,
        )
    for segment in segments:
        if segment.kind == "day_city" and segment.text.upper() in CURRENCY_CODES:
            _add_issue(
                issues,
                "currency_code_used_as_day_city",
                "error",
                "Currency code appears as a day city.",
                location=segment.location,
                excerpt=segment.text,
            )


def score_destination_truth(
    issues: list[OutputTextIssue],
    segments: Sequence[TextSegment],
    route_text: object,
) -> None:
    route = _clean_text(route_text)
    if route and ROUTE_FALSE_PLACE_RE.search(route):
        _add_issue(
            issues,
            "route_contains_service_as_destination",
            "error",
            "Route/destination line contains a service phrase instead of a real place.",
            location="cover.route",
            excerpt=route,
        )
    for segment in segments:
        if segment.kind != "day_city":
            continue
        city = _clean_text(segment.text)
        if not city:
            continue
        if ROUTE_FALSE_PLACE_RE.search(city):
            _add_issue(
                issues,
                "service_phrase_used_as_day_city",
                "error",
                "A service phrase appears as a day city.",
                location=segment.location,
                excerpt=city,
            )
        if AIRPORT_STAY_RE.search(city) and not re.search(
            r"\b(?:Keflavík|Longyearbyen)\b",
            city,
            flags=re.IGNORECASE,
        ):
            _add_issue(
                issues,
                "airport_used_as_stay_destination",
                "error",
                "Airport/service location appears as an overnight destination.",
                location=segment.location,
                excerpt=city,
            )


__all__ = ["score_city_currency_safety", "score_destination_truth"]
