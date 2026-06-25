"""Transport, arrival and departure day-render blocks."""

from __future__ import annotations

from itinerary_generation.content_engine import clean_client_title
from itinerary_generation.render_model import RenderBlock
from itinerary_generation.title_safety import is_forbidden_client_title
from text_polish import polish_title


def build_arrival_render_block(row):
    city = polish_title(row.get("city", ""))
    title = clean_client_title(row.get("title", ""), row)
    if is_forbidden_client_title(title) or not title or title.lower().strip(" .") in {"arrival", "arrival day", "welcome", "welcome day"}:
        title = f"Arrival in {city}" if city else "Arrival"
    return RenderBlock(
        kind="arrival",
        row_id=str(row.get("row_id") or ""),
        section_title="Arrival",
        title=title,
        css_class="arrival-block",
    )


def build_departure_render_block(row):
    title = clean_client_title(row.get("title", "") or "", row)
    if is_forbidden_client_title(title) or not title or title.lower().strip(" .") in {"departure", "departure day"}:
        title = "Journey home"
    return RenderBlock(
        kind="departure",
        row_id=str(row.get("row_id") or ""),
        section_title="Departure",
        title=title,
        css_class="departure-block",
    )


__all__ = ["build_arrival_render_block", "build_departure_render_block"]
