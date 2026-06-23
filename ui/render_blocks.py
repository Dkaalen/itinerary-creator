"""HTML renderer for UI-neutral itinerary render blocks."""

from __future__ import annotations

from itinerary_generation.render_model import RenderBlock
from ui.render_helpers import esc, render_list_items


_KIND_CLASS = {
    "activity": "activity-block",
    "group_tour_day": "activity-block group-tour-day-block",
    "accommodation": "accommodation-block",
    "leisure": "leisure-block",
    "cruise_leisure": "cruise-leisure-block",
    "arrival": "arrival-block",
    "departure": "departure-block",
    "included": "included-block",
    "day_overview": "day-overview-block",
    "optional_experience": "optional-experience-block",
    "travel_sequence": "travel-sequence-block",
    "transport": "transport-block",
    "self_transfer": "self-transfer-block",
    "self_arranged_travel": "self-arranged-block",
}


def _block_classes(block: RenderBlock) -> str:
    classes = ["content-block"]
    if block.css_class:
        classes.extend(str(block.css_class).split())
    else:
        classes.append(_KIND_CLASS.get(block.kind, f"{block.kind}-block" if block.kind else "generic-block"))
    return " ".join(dict.fromkeys(cls for cls in classes if cls))


def _data_row_attr(block: RenderBlock) -> str:
    # Preserve the legacy HTML shape for synthetic aggregate blocks that did not
    # carry a source-row data attribute before the render contract migration.
    if block.kind in {"travel_sequence", "included"}:
        return ""
    return f' data-row-id="{esc(block.row_id)}"' if block.row_id else ""



def _section_by_title(block: RenderBlock, title: str):
    target = str(title or "").strip().lower()
    for section in block.extra_sections or []:
        if str(section.title or "").strip().lower() == target:
            return section
    return None


def _meta_badges_html(block: RenderBlock) -> str:
    badges = []
    for meta in block.meta or []:
        if meta.value:
            label = f"{esc(meta.label)}: " if meta.label else ""
            badges.append(f'<span class="premium-travel-badge">{label}{esc(meta.value)}</span>')
    return f'<div class="premium-travel-badges">{"".join(badges)}</div>' if badges else ""


def _chips_html(items, class_name="premium-travel-chip") -> str:
    chips = [f'<span class="{esc(class_name)}">{esc(item)}</span>' for item in (items or []) if item]
    return f'<div class="premium-travel-chips">{"".join(chips)}</div>' if chips else ""


def _premium_timeline_html(items) -> str:
    clean_items = [item for item in (items or []) if item]
    if not clean_items:
        return ""
    html_text = '<div class="premium-travel-timeline">'
    for item in clean_items:
        html_text += f'<div class="premium-travel-timeline-item"><span></span><div>{esc(item)}</div></div>'
    html_text += '</div>'
    return html_text


def _render_premium_travel_block(block: RenderBlock) -> dict:
    classes = _block_classes(block)
    legacy_lines = " | ".join(str(line) for line in (block.lines or []) if line)
    legacy_attr = f' data-legacy-lines="{esc(legacy_lines)}"' if legacy_lines else ""
    html_text = f'<div class="{esc(classes)}"{legacy_attr}>'
    if block.section_title:
        html_text += f'<div class="section-title premium-travel-kicker">{esc(block.section_title)}</div>'
    if block.title:
        html_text += f'<div class="premium-travel-title">{esc(block.title)}</div>'
    if block.description:
        html_text += f'<div class="body-text premium-travel-description">{esc(block.description)}</div>'
    html_text += _meta_badges_html(block)

    route_section = _section_by_title(block, "Route")
    if route_section and route_section.items:
        html_text += f'<div class="premium-route-ribbon">{esc(route_section.items[0])}</div>'

    timeline = _section_by_title(block, "Journey timeline") or _section_by_title(block, "Coordinated day flow")
    if timeline and timeline.items:
        html_text += _premium_timeline_html(timeline.items)

    highlights = _section_by_title(block, "Highlights")
    if highlights and highlights.items:
        html_text += _chips_html(highlights.items)

    inclusions = _section_by_title(block, "Included journey") or _section_by_title(block, "Cruise inclusions")
    if inclusions and inclusions.items:
        html_text += f'<div class="section-title small-section">{esc(inclusions.title)}</div>'
        html_text += _chips_html(inclusions.items, "premium-travel-chip premium-travel-chip-muted")

    linked = _section_by_title(block, "Linked transfers")
    if linked and linked.items:
        html_text += '<div class="premium-linked-transfers">'
        html_text += '<div class="section-title small-section">Linked transfers</div>'
        for item in linked.items:
            html_text += f'<div class="body-text muted-note">{esc(item)}</div>'
        html_text += '</div>'

    html_text += "</div>"
    return {"kind": block.kind, "row_id": block.row_id, "html": html_text}

def render_block_to_html(block: RenderBlock) -> dict:
    if "premium-travel-card" in str(block.css_class or "").split():
        return _render_premium_travel_block(block)

    html_text = f'<div class="{esc(_block_classes(block))}"{_data_row_attr(block)}>'

    if block.section_title:
        html_text += f'<div class="section-title">{esc(block.section_title)}</div>'

    if block.title:
        html_text += f'<div class="body-text strong-line">{esc(block.title)}</div>'

    for meta in block.meta:
        if meta.value:
            html_text += f'<div class="body-text"><span class="meta-label">{esc(meta.label)}:</span> {esc(meta.value)}</div>'

    if block.kind in {"activity", "group_tour_day"}:
        if block.includes:
            included_label = "Included on This Tour Day" if block.kind == "group_tour_day" else "Included With This Experience"
            html_text += f'<div class="section-title small-section">{esc(included_label)}</div>'
            html_text += render_list_items(block.includes)
        if block.description:
            html_text += '<div class="section-title small-section">Description</div>'
            html_text += f'<div class="body-text muted-note">{esc(block.description)}</div>'
        if block.notable_sights:
            html_text += '<div class="section-title small-section">Notable Sights</div>'
            html_text += render_list_items(block.notable_sights)
    elif block.kind == "transport":
        if block.includes:
            html_text += '<div class="section-title small-section">Includes</div>'
            html_text += render_list_items(block.includes)
        if block.description:
            html_text += f'<div class="body-text muted-note">{esc(block.description)}</div>'
    elif block.kind == "accommodation":
        for line in block.lines:
            html_text += f'<div class="body-text muted-note">{esc(line)}</div>'
    else:
        if block.lines:
            html_text += render_list_items(block.lines)
        if block.description:
            note_class = "muted-note" if block.kind in {"self_transfer", "self_arranged_travel", "optional_experience"} else ""
            class_attr = f' class="body-text {note_class}"' if note_class else ' class="body-text"'
            html_text += f'<div{class_attr}>{esc(block.description)}</div>'

    for section in block.extra_sections:
        if section.items:
            html_text += f'<div class="section-title small-section">{esc(section.title)}</div>'
            html_text += render_list_items(section.items)

    html_text += "</div>"
    return {"kind": block.kind, "row_id": block.row_id, "html": html_text}


def render_blocks_to_html(blocks: list[RenderBlock]) -> str:
    return "".join(render_block_to_html(block)["html"] for block in blocks if block)
