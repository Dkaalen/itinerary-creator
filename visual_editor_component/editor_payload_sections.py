"""Top-level cover, summary, and generated-value payload helpers."""

from itinerary_generation.cover_route import clean_or_create_cover_route_line
from itinerary_generation.date_resolver import get_trip_date_range_text
from itinerary_generation.summaries import create_journey_arc, create_trip_glance
from itinerary_generation.titles import create_destinations_line, create_trip_subtitle, create_trip_title
from visual_editor_component.editor_payload_summary import _merge_trip_glance, _normalise_journey_arc


def build_cover_payload(parsed_rows, grouped_days, output_edits, typed_cover, cover_theme, cover_image, summary_image):
    return {
        "cover_kicker": typed_cover.get("cover_kicker") or output_edits.get("cover_kicker", "Travel Itinerary"),
        "route_label": typed_cover.get("route_label") or output_edits.get("route_label", "Route"),
        "cover_season": cover_theme.get("season", "summer"),
        "cover_background_data_uri": cover_theme.get("background_data_uri", ""),
        "cover_image": cover_image,
        "summary_image": summary_image,
        "cover_ink": cover_theme.get("ink", "#1f3446"),
        "cover_muted": cover_theme.get("muted", "#7b746c"),
        "cover_accent": cover_theme.get("accent", "#b89555"),
        "trip_title": typed_cover.get("trip_title") or output_edits.get("trip_title", create_trip_title(parsed_rows, grouped_days)),
        "trip_subtitle": typed_cover.get("trip_subtitle") or output_edits.get("trip_subtitle", create_trip_subtitle(parsed_rows, grouped_days)),
        "trip_dates": typed_cover.get("trip_dates") or output_edits.get("trip_dates") or get_trip_date_range_text(parsed_rows),
        "destinations_line": clean_or_create_cover_route_line(
            parsed_rows,
            typed_cover.get("destinations_line") or output_edits.get("destinations_line") or create_destinations_line(parsed_rows),
        ),
    }


def build_summary_payload(parsed_rows, grouped_days, output_edits, typed_summary):
    return {
        "trip_glance_title": typed_summary.get("trip_glance_title") or output_edits.get("trip_glance_title", "Your Trip at a Glance"),
        "journey_arc_title": typed_summary.get("journey_arc_title") or output_edits.get("journey_arc_title", "How Your Trip Unfolds"),
        "journey_arc_columns": typed_summary.get("journey_arc_columns") or output_edits.get("journey_arc_columns") or {"chapter": "Chapter", "days": "Days", "experience": "What You’ll Experience"},
        "trip_glance": _merge_trip_glance(
            parsed_rows,
            grouped_days,
            output_edits.get("trip_glance"),
            typed_summary.get("trip_glance"),
        ),
        "journey_arc": _normalise_journey_arc(
            grouped_days,
            typed_summary.get("journey_arc") or output_edits.get("journey_arc"),
        ),
    }


def build_generated_values(parsed_rows, grouped_days, generated_days_values, final_generated_values):
    return {
        "cover": {
            "cover_kicker": "Travel Itinerary",
            "route_label": "Route",
            "trip_title": create_trip_title(parsed_rows, grouped_days),
            "trip_subtitle": create_trip_subtitle(parsed_rows, grouped_days),
            "trip_dates": get_trip_date_range_text(parsed_rows),
            "destinations_line": clean_or_create_cover_route_line(parsed_rows, create_destinations_line(parsed_rows)),
        },
        "summary": {
            "trip_glance_title": "Your Trip at a Glance",
            "journey_arc_title": "How Your Trip Unfolds",
            "journey_arc_columns": {"chapter": "Chapter", "days": "Days", "experience": "What You’ll Experience"},
            "trip_glance": create_trip_glance(parsed_rows, grouped_days),
            "journey_arc": create_journey_arc(grouped_days),
        },
        "days": generated_days_values,
        "final_pages": final_generated_values,
    }
