"""Client-visible text segment extraction for real-output QA."""

from __future__ import annotations

from typing import Any

from scripts.real_output_qa.models import TextSegment
from scripts.real_output_qa.text_utils import clean_text as _clean_text, clip as _clip

def optional_addon_line(item: Any) -> str:
    if isinstance(item, dict):
        day = _clean_text(item.get("day"))
        title = _clean_text(item.get("title"))
        city = _clean_text(item.get("city"))
        description = _clean_text(item.get("description"))
        includes = [_clean_text(value) for value in item.get("includes", []) or () if _clean_text(value)]
        parts = [part for part in (day, city, title, description) if part]
        if includes:
            parts.append("Includes: " + "; ".join(includes[:4]))
        return _clip(" — ".join(parts), limit=420)
    return _clip(str(item), limit=420)



def iter_output_segments(context: Any) -> tuple[TextSegment, ...]:
    segments: list[TextSegment] = []
    render_document = getattr(context, "render_document", None)
    _append_segment(segments, "cover.trip_title", "trip_title", getattr(context, "trip_title", ""))
    _append_segment(segments, "cover.trip_subtitle", "trip_subtitle", getattr(context, "trip_subtitle", ""))
    _append_segment(segments, "cover.route", "route", getattr(context, "destinations_line", "") or getattr(render_document, "route", ""))
    for index, arc in enumerate(getattr(context, "journey_arc", []) or (), start=1):
        if isinstance(arc, dict):
            _append_segment(segments, f"journey_arc[{index}]", "journey_arc", " · ".join(_clean_text(value) for value in arc.values() if _clean_text(value)))
    for index, item in enumerate(getattr(context, "whats_included", []) or (), start=1):
        _append_segment(segments, f"included[{index}]", "included", item)
    for index, item in enumerate(getattr(context, "optional_addons", []) or (), start=1):
        _append_segment(segments, f"optional_addons[{index}]", "optional_addon", optional_addon_line(item))
    for index, item in enumerate(getattr(context, "whats_not_included", []) or (), start=1):
        _append_segment(segments, f"not_included[{index}]", "not_included", item)
    for day in getattr(render_document, "days", []) or ():
        day_id = _clean_text(getattr(day, "day", ""))
        _append_segment(segments, f"{day_id}.title", "day_title", getattr(day, "title", ""), day=day_id)
        _append_segment(segments, f"{day_id}.city", "day_city", getattr(day, "city", ""), day=day_id)
        _append_segment(segments, f"{day_id}.intro", "day_intro", getattr(day, "intro", ""), day=day_id)
        for block_index, block in enumerate(getattr(day, "blocks", []) or (), start=1):
            block_kind = _clean_text(getattr(block, "kind", "block")) or "block"
            base = f"{day_id}.{block_kind}[{block_index}]"
            _append_segment(segments, f"{base}.section", f"{block_kind}_section", getattr(block, "section_title", ""), day=day_id)
            _append_segment(segments, f"{base}.title", f"{block_kind}_title", getattr(block, "title", ""), day=day_id)
            _append_segment(segments, f"{base}.description", f"{block_kind}_description", getattr(block, "description", ""), day=day_id)
            for line_index, line in enumerate(getattr(block, "lines", []) or (), start=1):
                _append_segment(segments, f"{base}.line[{line_index}]", f"{block_kind}_line", line, day=day_id)
            for include_index, include in enumerate(getattr(block, "includes", []) or (), start=1):
                _append_segment(segments, f"{base}.include[{include_index}]", f"{block_kind}_include", include, day=day_id)
            for meta_index, meta in enumerate(getattr(block, "meta", []) or (), start=1):
                _append_segment(
                    segments,
                    f"{base}.meta[{meta_index}]",
                    f"{block_kind}_meta",
                    f"{_clean_text(getattr(meta, 'label', ''))}: {_clean_text(getattr(meta, 'value', ''))}",
                    day=day_id,
                )
    return tuple(segments)


def _append_segment(segments: list[TextSegment], location: str, kind: str, text: object, *, day: str = "") -> None:
    cleaned = _clean_text(text)
    if cleaned:
        segments.append(TextSegment(location=location, kind=kind, text=cleaned, day=day))


def rendered_output_text(context: Any) -> str:
    return "\n".join(segment.text for segment in iter_output_segments(context))



# Legacy private alias for compatibility through scripts.real_output_text_quality.
_optional_addon_line = optional_addon_line

__all__ = ["iter_output_segments", "optional_addon_line", "rendered_output_text", "_optional_addon_line"]
