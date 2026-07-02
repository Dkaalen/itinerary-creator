"""Convert canonical group-tour days into render blocks."""

import re
from typing import Any, Mapping

from itinerary_generation.group_tour_domain import GroupTourDay, group_tour_day_from_row
from itinerary_generation.group_tour_render_titles import group_tour_day_title
from itinerary_generation.group_tour_render_utils import clean, natural_join, unique
from itinerary_generation.render_model import RenderBlock, RenderMetaLine, RenderSection
from itinerary_generation.time_display import display_time
from text_polish import polish_client_text


def _fact_description(segment: GroupTourDay) -> str:
    source = polish_client_text(segment.description)
    if source:
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", source) if item.strip()]; useful = []
        raw_supplier_markers = (
            "prepare to explore amazing things",
            "thirsty?",
            "instant foot wetness",
        )
        if any(marker in source.casefold() for marker in raw_supplier_markers):
            return ""
        for sentence in sentences:
            if any(marker in sentence.casefold() for marker in ("book this", "check availability", "what are you waiting", "price is per")): continue
            useful.append(sentence)
            if len(useful) >= 3: break
        for sentence in sentences[3:]:
            if re.search(r"\b(return|head back|spend the night|overnight|accommodation)\b", sentence, flags=re.IGNORECASE) and sentence not in useful: useful.append(sentence); break
        summary = " ".join(useful).strip()
        if summary: return summary if len(summary) <= 720 else summary[:717].rstrip(" ,;:") + "..."
    route, highlights = unique(segment.route), unique(segment.included_activities or segment.highlights)
    if route and highlights: return polish_client_text(f"Travel through {natural_join(route)}, with planned visits including {natural_join(highlights[:6])}.")
    if route: return polish_client_text(f"Travel through {natural_join(route)}.")
    return polish_client_text(f"Today’s guided programme includes {natural_join(highlights[:6])}.") if highlights else ""


def _accommodation_display(value: str) -> str:
    text = re.sub(r"\b(?:w\s*/|with)\s*breakfast\b", "breakfast included", clean(value), flags=re.IGNORECASE)
    match = re.fullmatch(r"(?P<place>[A-Za-zÀ-ÿØøÅåÆæÄäÖö .'-]+?)\s+(?P<lodging>hotel|guesthouse)\s+breakfast included\.?", text, flags=re.IGNORECASE)
    if match: text = f"Breakfast included at {match.group('place').strip()} {match.group('lodging').lower()}"
    if text and not text.endswith((".", "!", "?")): text += "."
    return polish_client_text(text)


def build_group_tour_day_render_block(row: Mapping[str, Any]) -> RenderBlock | None:
    segment = group_tour_day_from_row(row)
    if segment is None: return None
    context = row.get("group_tour_package_context") if isinstance(row.get("group_tour_package_context"), Mapping) else {}; duration = int(context.get("duration_days") or 0)
    section_title = f"Group Tour · Day {segment.package_day_number}" + (f" of {duration}" if duration else "")
    meta = []
    if segment.package_day_number == 1:
        pickup, meeting = display_time(context.get("pickup_time", "")) or clean(context.get("pickup_time")), clean(context.get("meeting_point"))
        if pickup: meta.append(RenderMetaLine("Pick-up", pickup))
        if meeting: meta.append(RenderMetaLine("Meeting point", meeting))
    if segment.route: meta.append(RenderMetaLine("Route", " → ".join(unique(segment.route))))
    sections = []
    if segment.meals: sections.append(RenderSection("Meals", unique(segment.meals)))
    if segment.accommodation_note: sections.append(RenderSection("Included Overnight", [_accommodation_display(segment.accommodation_note)]))
    if segment.conditional_items: sections.append(RenderSection("Important Conditions", [polish_client_text(item) for item in segment.conditional_items]))
    if segment.optional_items: sections.append(RenderSection("Optional During This Tour Day", [polish_client_text(item) for item in segment.optional_items]))
    row_id = str(row.get("row_id") or "")
    return RenderBlock(kind="group_tour_day", row_id=row_id, section_title=section_title, title=group_tour_day_title([row]), meta=meta, includes=unique(segment.included_activities)[:8], description=_fact_description(segment), extra_sections=sections, css_class="activity-block group-tour-day-block", source_row_ids=list(segment.source_row_ids) or ([row_id] if row_id else []), warnings=list(segment.warnings))
