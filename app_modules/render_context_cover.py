"""Cover-page render contract helpers."""

from __future__ import annotations

from typing import Any

from itinerary_generation.editor_page_contract import page_is_hidden as contract_page_is_hidden
from itinerary_generation.render_model import RenderCover


def build_render_cover(context: Any) -> RenderCover | None:
    """Build the typed PDF/preview cover contract from a render context."""

    if contract_page_is_hidden(context.hidden_page_ids, "cover"):
        return None
    return RenderCover(
        kicker=context.cover_kicker,
        route_label=context.cover_route_label,
        title=context.trip_title,
        subtitle=context.trip_subtitle,
        dates=context.trip_dates,
        route=context.destinations_line,
        background_path=context.cover_background_path,
        crop_focus=context.cover_crop_focus,
        ink=str(context.cover_theme.get("ink", "")),
        muted=str(context.cover_theme.get("muted", "")),
        accent=str(context.cover_theme.get("accent", "")),
        season=str(context.cover_theme.get("season", "")),
    )
