"""Northern Lights activity-title fallbacks.

Kept separate from ``activity_titles_core`` so the core title function can
orchestrate product matching without owning every family-specific phrase rule.
"""

from __future__ import annotations


def looks_like_northern_lights_activity(title_text: str, full_text: str) -> bool:
    """Return whether the row should use Northern Lights fallback titling."""

    title_has_northern_lights = (
        "northern light" in title_text
        or "aurora" in title_text
        or "borealis" in title_text
    )
    full_has_northern_lights = (
        "northern light" in full_text
        or "aurora" in full_text
        or "borealis" in full_text
    )
    title_has_activity_word = any(
        word in title_text
        for word in ["hunt", "chase", "basecamp", "base camp", "cruise", "boat", "float", "floating", "mileage"]
    )
    # Do not rename ordinary daytime/culture activities just because the long
    # supplier description mentions a chance of seeing northern lights.
    return title_has_northern_lights or (
        full_has_northern_lights
        and (
            title_has_activity_word
            or any(
                word in full_text
                for word in ["northern lights cruise", "aurora cruise", "aurora basecamp", "ice floating"]
            )
        )
    )


def northern_lights_activity_title(full_text: str) -> str:
    """Return a deterministic client-facing Northern Lights title."""

    if "reindeer" in full_text and ("hunt" in full_text or "hunting" in full_text or "chase" in full_text):
        return "Northern Lights Hunt by Reindeer"
    if "aurora basecamp" in full_text or "aurora base camp" in full_text:
        return "Northern Lights Safari to Aurora Basecamp" if "safari" in full_text else "Aurora Basecamp"
    if "basecamp" in full_text or "base camp" in full_text:
        return "Northern Lights Basecamp"
    if "cruise" in full_text or "boat" in full_text or "sailing" in full_text:
        return "Northern Lights Cruise"
    if "floating" in full_text or "float" in full_text:
        return "Northern Lights Ice Floating"
    if "chase" in full_text:
        return "Northern Lights Chase"
    if "hunt" in full_text or "mileage" in full_text or "photo tour" in full_text:
        return "Northern Lights Hunt"
    return "Northern Lights Experience"


__all__ = ["looks_like_northern_lights_activity", "northern_lights_activity_title"]
