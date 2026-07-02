"""Summary-page source data preparation for itinerary render context."""

from __future__ import annotations

from typing import Any

from itinerary_generation.summaries import create_journey_arc, create_trip_glance, sanitize_journey_arc_experience
from app_modules.render_context_cover_data import _safe_label
from app_modules.presentation_language import label_for


def _saved_journey_arc_is_usable(saved_journey_arc: Any) -> bool:
    weak_arc_markers = (
        "onward flight",
        "onward travel",
        "onward train",
        "onward connection",
        "flight connection",
        "travel continues",
        "aurora",
    )
    return bool(
        isinstance(saved_journey_arc, list)
        and saved_journey_arc
        and not any(
            any(marker in str(row.get("experience", "")).lower() for marker in weak_arc_markers)
            for row in saved_journey_arc
            if isinstance(row, dict)
        )
    )


def build_summary_context_data(parsed_rows, grouped_days, output_edits: dict[str, Any], editor_draft: dict[str, Any]) -> dict[str, Any]:
    """Build trip-glance and journey-arc fields for render context."""

    typed_summary = editor_draft.get("summary", {}) if isinstance(editor_draft.get("summary"), dict) else {}
    raw_arc_columns = typed_summary.get("journey_arc_columns") if isinstance(typed_summary.get("journey_arc_columns"), dict) else output_edits.get("journey_arc_columns")
    raw_arc_columns = raw_arc_columns if isinstance(raw_arc_columns, dict) else {}
    journey_arc_columns = {
        "chapter": _safe_label(raw_arc_columns.get("chapter"), label_for(output_edits, "chapter", "Chapter")),
        "days": _safe_label(raw_arc_columns.get("days"), label_for(output_edits, "days", "Days")),
        "experience": _safe_label(raw_arc_columns.get("experience"), label_for(output_edits, "experience", "What You’ll Experience")),
    }

    trip_glance = create_trip_glance(parsed_rows, grouped_days)
    saved_trip_glance = typed_summary.get("trip_glance") or output_edits.get("trip_glance") or {}
    if isinstance(saved_trip_glance, dict):
        for label, value in saved_trip_glance.items():
            if label in trip_glance:
                trip_glance[label] = value
    generated_trip_glance = create_trip_glance(parsed_rows, grouped_days)
    for route_label in ("Start", "End", "Destinations"):
        if route_label in generated_trip_glance:
            trip_glance[route_label] = generated_trip_glance[route_label]

    saved_journey_arc = typed_summary.get("journey_arc") or output_edits.get("journey_arc")
    if _saved_journey_arc_is_usable(saved_journey_arc):
        journey_arc = [
            {
                "chapter": str(row.get("chapter", "")).strip(),
                "days": str(row.get("days", "")).strip(),
                "experience": sanitize_journey_arc_experience(row.get("experience", ""), chapter=row.get("chapter", "")),
            }
            for row in saved_journey_arc
            if isinstance(row, dict)
        ]
    else:
        journey_arc = create_journey_arc(grouped_days)

    return {
        "trip_glance_title": _safe_label(typed_summary.get("trip_glance_title") or output_edits.get("trip_glance_title"), label_for(output_edits, "trip_glance", "Your Trip at a Glance")),
        "trip_glance": trip_glance,
        "journey_arc_title": _safe_label(typed_summary.get("journey_arc_title") or output_edits.get("journey_arc_title"), label_for(output_edits, "journey_arc", "Your Journey Arc")),
        "journey_arc_columns": journey_arc_columns,
        "journey_arc": journey_arc,
    }


__all__ = ["build_summary_context_data"]
