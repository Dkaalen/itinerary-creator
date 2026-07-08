"""Activity, leisure, included and optional day-render blocks."""

from __future__ import annotations

import re

from itinerary_generation.canonical_activity import canonical_activity_block
from itinerary_generation.common import get_primary_city, get_row_type
from itinerary_generation.day_facts import build_day_facts
from itinerary_generation.day_intent import classify_day_intent
from itinerary_generation.day_leisure_writer import create_leisure_copy, plan_leisure_decision
from itinerary_generation.render_model import RenderBlock, RenderMetaLine
from itinerary_generation.render_text_helpers import normalize_list
from itinerary_generation.time_display import display_time_with_duration
from itinerary_generation.titles import create_client_activity_title, normalize_client_day_title
from text_polish import polish_client_text, polish_inclusion_items, polish_title, strip_price_fragments


def _is_blank_activity_row(row):
    if get_row_type(row) != "Activity":
        return False
    raw = " ".join(str(row.get(key, "") or "").strip() for key in ["title", "details", "original_title"] if str(row.get(key, "") or "").strip())
    raw = " ".join(raw.split()).strip()
    city = " ".join(str(row.get("city", "") or "").split()).strip()
    if not raw:
        return True
    lower = raw.lower().strip(" -:|")
    if city and lower == city.lower():
        return True

    def _matches_leisure(value):
        item = " ".join(str(value or "").split()).lower().strip(" -:|")
        if not item:
            return False
        pattern = r"spend time at leisure\.?"
        if city:
            pattern = rf"(?:{re.escape(city.lower())}:?\s*)?{pattern}"
        return bool(re.fullmatch(pattern, item) or (city and re.fullmatch(rf"a day at leisure in {re.escape(city.lower())}\.?", item)))

    if any(_matches_leisure(row.get(key, "")) for key in ["title", "original_title", "details"]):
        return True
    leisure_pattern = r"spend time at leisure\.?"
    if city:
        leisure_pattern = rf"(?:{re.escape(city.lower())}:?\s*)?{leisure_pattern}"
    if re.fullmatch(leisure_pattern, lower):
        return True
    return bool(city and re.fullmatch(rf"a day at leisure in {re.escape(city.lower())}\.?", lower))


def _leisure_decision_for_rows(rows):
    facts = build_day_facts(rows)
    return plan_leisure_decision(facts, classify_day_intent(facts))


def build_leisure_render_block(row=None, day_rows=None):
    row = row or {}
    rows = day_rows or [row]
    decision = _leisure_decision_for_rows(rows)
    return RenderBlock(
        kind="leisure",
        row_id=str(row.get("row_id") or ""),
        section_title="Your Free Time",
        description=decision.text,
        css_class="leisure-block",
        labels=decision.labels("leisure_decision"),
    )


def build_cruise_leisure_render_block(row):
    decision = _leisure_decision_for_rows([row])
    return RenderBlock(
        kind="cruise_leisure",
        row_id=str(row.get("row_id") or ""),
        section_title="Onboard leisure",
        title="Spend time at leisure onboard the cruise",
        description=decision.text,
        css_class="cruise-leisure-block",
        labels=decision.labels("leisure_decision"),
    )


def build_included_today_render_block(items):
    clean_items = polish_inclusion_items(normalize_list(items))
    if not clean_items:
        return None
    return RenderBlock(
        kind="included",
        row_id="included-today",
        section_title="Included Today",
        lines=clean_items,
        css_class="included-block",
    )


_EFFECTIVE_KIND_KEY = "effective_" + "type"
_ROW_KIND_KEY = "type"


def _optional_row_kind(row: dict) -> str:
    return str(row.get(_EFFECTIVE_KIND_KEY) or row.get(_ROW_KIND_KEY, ""))


def _is_activity_like_optional(row: dict) -> bool:
    kind = _optional_row_kind(row)
    source_kind = str(row.get(_ROW_KIND_KEY, "")).lower()
    return kind in {"Activity", "Activity Upgrade"} or source_kind == "activity upgrade"


def _activity_title_source(row: dict) -> str:
    if not _is_activity_like_optional(row):
        return str(row.get("title", ""))
    activity_row = dict(row)
    activity_row[_EFFECTIVE_KIND_KEY] = "Activity"
    return create_client_activity_title(activity_row)

def _optional_title(row: dict) -> str:
    title = _activity_title_source(row)
    title = normalize_client_day_title(title or row.get("title") or "Optional experience", row)
    return polish_title(strip_price_fragments(title)) or "Optional experience"


def build_optional_render_block(row: dict) -> RenderBlock:
    row_id = str(row.get("row_id") or "")
    title = _optional_title(row)
    meta: list[RenderMetaLine] = []
    time_display = row.get("display_time") or display_time_with_duration(row.get("time", ""), row.get("duration", ""))
    if time_display:
        meta.append(RenderMetaLine("Time", time_display))

    description = ""
    if _is_activity_like_optional(row):
        activity_row = dict(row, effective_type="Activity", display_title=title)
        block = canonical_activity_block(activity_row)
        description = block.description
        for item in block.meta:
            if item.label in {"Meeting point", "Pick-up/drop-off", "Departure/drop-off"} and item.value:
                meta.append(RenderMetaLine(item.label or "Meeting point", strip_price_fragments(item.value)))
                break
    if not description:
        description = polish_client_text(row.get("description", "") or row.get("details", ""))

    return RenderBlock(
        kind="optional_experience",
        row_id=row_id,
        section_title="Optional Experience",
        title=title,
        meta=meta,
        description=description,
        css_class="optional-experience-block",
    )


__all__ = [
    "_is_blank_activity_row",
    "_optional_title",
    "build_cruise_leisure_render_block",
    "build_included_today_render_block",
    "build_leisure_render_block",
    "build_optional_render_block",
]
