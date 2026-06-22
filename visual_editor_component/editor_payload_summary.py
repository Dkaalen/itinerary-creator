"""Summary payload helpers for the visual editor."""

from itinerary_generation.summaries import (
    create_journey_arc,
    create_trip_glance,
    sanitize_journey_arc_experience,
)


def _merge_trip_glance(parsed_rows, grouped_days, *saved_glances):
    generated = create_trip_glance(parsed_rows, grouped_days)
    for saved in saved_glances:
        if isinstance(saved, dict):
            for key, value in saved.items():
                if key in generated:
                    generated[key] = value
    # Route-owned fields are never editable fallbacks: saved drafts can be old
    # or polluted by transfer rows, so regenerate them from overnight stays.
    route_owned = create_trip_glance(parsed_rows, grouped_days)
    for key in ("Start", "End", "Destinations"):
        if key in route_owned:
            generated[key] = route_owned[key]
    return generated


def _get_trip_glance(parsed_rows, grouped_days, output_edits):
    return _merge_trip_glance(parsed_rows, grouped_days, (output_edits or {}).get("trip_glance"))


def _normalise_journey_arc(grouped_days, saved):
    weak_arc_markers = (
        "onward flight",
        "onward travel",
        "onward train",
        "onward connection",
        "flight connection",
        "travel continues",
        "aurora",
    )
    if isinstance(saved, list) and saved:
        clean_rows = []
        should_regenerate = False
        for row in saved:
            if isinstance(row, dict):
                chapter = str(row.get("chapter", "")).strip()
                experience = str(row.get("experience", "")).strip()
                if any(marker in experience.lower() for marker in weak_arc_markers):
                    should_regenerate = True
                    break
                clean_rows.append({
                    "chapter": chapter,
                    "days": str(row.get("days", "")).strip(),
                    "experience": sanitize_journey_arc_experience(experience, chapter=chapter),
                })
        if clean_rows and not should_regenerate:
            return clean_rows
    return create_journey_arc(grouped_days)


def _get_journey_arc(grouped_days, output_edits):
    return _normalise_journey_arc(grouped_days, (output_edits or {}).get("journey_arc"))
