"""Whole-day title composition for arranged activities plus route travel.

This module owns the cross-domain decision for days that contain both a real
activity and meaningful transport. Activity identity and transport identity are
resolved elsewhere; this module only decides how those two established facts
share one day heading.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from itinerary_generation.copy_decision_contract import (
    CopyDecisionTrace,
    decision_candidate,
    finalize_decision,
)
from itinerary_generation.title_decision_contract import join_title_text
from text_polish import polish_title

if TYPE_CHECKING:
    from itinerary_generation.day_facts import DayFacts


def compose_activity_overnight_transport_title(
    *,
    activity_trace: CopyDecisionTrace,
    transport_title: str,
    facts: "DayFacts",
) -> CopyDecisionTrace | None:
    """Return a title for an activity followed by confirmed overnight travel.

    An overnight departure is not an arrival-day signal. It therefore cannot
    be expressed as ``Arrival in <destination>`` merely because the route
    endpoint becomes the day's final city fact.
    """

    if not facts.has_overnight_transport or not activity_trace.text:
        return None

    destination = polish_title(facts.route_destination or facts.end_city or facts.onward_destination or "")
    route_title = polish_title(transport_title)
    if not route_title and destination:
        route_title = f"Overnight Train to {destination}" if facts.has_train else f"Overnight Travel to {destination}"
    if not route_title:
        route_title = "Overnight Travel"

    title = join_title_text(activity_trace.text, route_title, max_length=96)
    selected = decision_candidate(
        title,
        source="activity_overnight_transport_composed_title",
        priority=97,
        reason="The day combines a source-backed activity with confirmed overnight departure travel; neither fact should be recast as an arrival.",
    )
    transport_candidate = decision_candidate(
        route_title,
        source="transport_title",
        priority=84,
        reason="Transport domain provided the overnight route identity used by the composed day title.",
    )
    assert selected is not None
    return finalize_decision(
        kind="day_title",
        selected=selected,
        candidates=(*activity_trace.candidates, transport_candidate),
        context={
            "intent": "activity_plus_overnight_transport",
            "destination": destination,
        },
    )


__all__ = ["compose_activity_overnight_transport_title"]
