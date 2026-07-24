"""Summary-page render contract helpers."""

from __future__ import annotations

from typing import Any

from itinerary_generation.summaries import sanitize_journey_arc_experience
from itinerary_generation.editor_page_contract import page_is_hidden as contract_page_is_hidden
from itinerary_generation.render_model import RenderMetaLine, RenderSummary


def build_render_summary(context: Any, *, include_hidden: bool = False) -> RenderSummary | None:
    """Build the typed PDF/preview summary contract from a render context."""

    if not include_hidden and contract_page_is_hidden(context.hidden_page_ids, "summary"):
        return None
    return RenderSummary(
        trip_glance_title=context.trip_glance_title,
        trip_glance=[RenderMetaLine(str(label), str(value)) for label, value in context.trip_glance.items()],
        journey_arc_title=context.journey_arc_title,
        journey_arc_columns=dict(context.journey_arc_columns or {}),
        journey_arc=[
            {
                "chapter": str(row.get("chapter", "")).strip(),
                "days": str(row.get("days", "")).strip(),
                "experience": sanitize_journey_arc_experience(row.get("experience", ""), chapter=row.get("chapter", "")),
            }
            for row in context.journey_arc
            if isinstance(row, dict)
        ],
        background_path=context.summary_background_path,
        crop_focus=context.summary_crop_focus,
    )
