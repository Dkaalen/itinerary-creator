"""Duration extraction helpers for parser time fields."""

from __future__ import annotations

import re

from time_duration import format_duration_display
from shared.text import clean_space
from shared.source_time_normalize import normalize_time_text


def normalize_duration_text(value):
    duration = clean_space(value)
    if not duration:
        return ""

    duration = duration.replace("–", "-")
    already_expanded = re.search(r"\b\d+\s+hours?\s+\d+\s+minutes?\b", duration, flags=re.IGNORECASE)
    if already_expanded:
        return already_expanded.group(0)

    range_hours = re.search(
        r"\b(\d+(?:\s*[.,]\s*\d+)?)\s*(?:-|to)\s*(\d+(?:\s*[.,]\s*\d+)?)\s*(?:h|hr|hrs|hour|hours)\b",
        duration,
        flags=re.IGNORECASE,
    )
    if range_hours:
        start = re.sub(r"\s*\.\s*", ".", range_hours.group(1)).replace(" ", "").replace(",", ".")
        end = re.sub(r"\s*\.\s*", ".", range_hours.group(2)).replace(" ", "").replace(",", ".")
        return f"{start}–{end} hours"

    minute_match = re.search(r"\b(\d+\s*(?:-|–)\s*\d+\s*minutes?)\b", duration, flags=re.IGNORECASE)
    if minute_match:
        return minute_match.group(1).replace("-", "–")

    # Defensive cleanup: sometimes a colleague-style cell has
    # "3 Hrs Overview ..." in the same pipe section. Keep only the actual
    # duration phrase and discard any following supplier description.
    match = re.search(
        r"\b((?:Cruise\s+Duration|Tour\s+Duration|Duration)?\s*:?\s*\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour))\b",
        duration,
        flags=re.IGNORECASE,
    )
    if match:
        duration = match.group(1)

    duration = re.sub(r"\bCruise\s+Duration\b", "Cruise duration", duration, flags=re.IGNORECASE)
    duration = re.sub(r"\bTour\s+Duration\b", "Duration", duration, flags=re.IGNORECASE)
    duration = re.sub(r"\bDuration\s*:\s*", "Duration ", duration, flags=re.IGNORECASE)
    return format_duration_display(duration)


def split_time_and_duration(value):
    text = clean_space(value)
    if not text:
        return "", ""

    duration = ""
    patterns = [
        r"\b(Cruise\s+Duration\s+\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour))\b",
        r"\b(Duration\s*:?\s*\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour))\b",
        r"\b(\d+(?:\s*[.,]\s*\d+)?\s*(?:Hrs|Hr|hours|hour))\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            duration = normalize_duration_text(match.group(1))
            text = (text[:match.start()] + text[match.end():]).strip(" -|:")
            break

    text = re.sub(r"\b0(\d):(\d{2})\s*pm\b", r"\1:\2 pm", text, flags=re.IGNORECASE)
    text = re.sub(r"\b0(\d):(\d{2})\s*am\b", r"\1:\2 am", text, flags=re.IGNORECASE)

    return normalize_time_text(text), duration
