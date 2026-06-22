"""Build visual editor payloads from itinerary state."""

import hashlib
from pathlib import Path

from itinerary_generation.common import get_primary_city
from itinerary_generation.day_text import create_day_intro, create_travel_route_label
from itinerary_generation.titles import (
    create_day_title,
    create_destinations_line,
    create_trip_subtitle,
    create_trip_title,
)
from itinerary_generation.cover_route import clean_or_create_cover_route_line
from itinerary_generation.cover_theme import get_cover_theme
from itinerary_generation.cover_assets import resolve_cover_background
from itinerary_generation.date_resolver import get_day_date_text, get_trip_date_range_text
from itinerary_generation.inclusions import create_whats_not_included
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.group_tour_rendering import (
    group_tour_day_city,
    group_tour_day_from_rows,
    group_tour_day_intro,
    group_tour_day_title,
)
from itinerary_generation.structured_html_audit import validate_source_aware_html_coverage
from itinerary_generation.transport_safety import scan_client_output
from itinerary_generation.summaries import (
    create_journey_arc,
    create_trip_glance,
    sanitize_journey_arc_experience,
)
from images.app_image_selection import (
    get_day_image_choice,
    get_day_image_crop_focus,
    get_image_preview_for_path,
    list_replacement_image_options_for_rows,
    audit_day_image_matches,
    select_day_images_with_overrides,
)
from ui.day_pages import render_inclusion_sections_inner_html, render_inclusion_page_inner_htmls
from ui.day_blocks import build_day_blocks
from ui.render_helpers import get_detail_level_name, list_to_text
from ui.picture_workflow import pictures_are_added
from itinerary_generation.editable_draft import (
    day_by_id,
    first_block_html,
    normalise_editable_draft,
    section_by_id,
)
from itinerary_generation.editor_page_contract import build_editor_document_pages


def _source_signature(parsed_rows, grouped_days):
    """Stable signature for the source itinerary behind the editor draft.

    Browser-local draft recovery is useful, but only while the editor is still
    looking at the same generated itinerary.  This signature prevents a stale
    localStorage draft from being merged into a different itinerary/project.
    """
    pieces = []
    rows = parsed_rows or []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        pieces.append("|".join([
            str(row.get("row_id") or row.get("line_number") or index),
            str(row.get("day") or ""),
            str(row.get("date") or row.get("start_date") or ""),
            str(row.get("type") or row.get("effective_type") or ""),
            str(row.get("city") or row.get("destination") or ""),
            str(row.get("title") or row.get("original_title") or ""),
            str(row.get("raw_text") or row.get("details") or ""),
        ]))
    if not pieces and grouped_days:
        for day, day_rows in grouped_days.items():
            pieces.append(str(day))
            for row in day_rows or []:
                pieces.append(str(row.get("row_id") or row.get("title") or row))
    payload = "\n".join(pieces)
    return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()[:20]

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


def _build_generated_inclusion_sections(parsed_rows, grouped_days):
    return build_itinerary_document(parsed_rows, grouped_days).inclusions


def _build_generated_inclusions_html(parsed_rows, grouped_days):
    return render_inclusion_sections_inner_html(_build_generated_inclusion_sections(parsed_rows, grouped_days))


def _build_generated_inclusion_page_htmls(parsed_rows, grouped_days):
    return render_inclusion_page_inner_htmls(_build_generated_inclusion_sections(parsed_rows, grouped_days))


def _build_generated_exclusions_html(parsed_rows, grouped_days=None):
    return render_inclusion_sections_inner_html(build_itinerary_document(parsed_rows, grouped_days).exclusions)


def _compact_model_warnings(structured_document, parsed_rows=None):
    warnings = []
    seen = set()
    row_lookup = {str(row.get("row_id") or ""): row for row in (parsed_rows or []) if isinstance(row, dict)}
    for warning in getattr(structured_document, "warnings", ()) or ():
        key = (warning.code, warning.message, tuple(warning.source_row_ids))
        if key in seen:
            continue
        seen.add(key)
        source_ids = list(warning.source_row_ids)
        source_row = next((row_lookup.get(str(row_id)) for row_id in source_ids if row_lookup.get(str(row_id))), None)
        page_label = ""
        if source_row:
            day = str(source_row.get("day") or "").strip()
            title = str(source_row.get("title") or source_row.get("original_title") or "").strip()
            city = str(source_row.get("city") or "").strip()
            bits = [bit for bit in (day, city, title) if bit]
            page_label = " · ".join(bits[:3])
        warnings.append({
            "code": warning.code,
            "severity": warning.severity,
            "message": warning.message,
            "excerpt": warning.message,
            "page_label": page_label or "Structured itinerary",
            "source_row_ids": source_ids,
        })
    return warnings[:30]


def _page_html_payload(page_htmls):
    pages = page_htmls if isinstance(page_htmls, list) else [page_htmls]
    return [{"html": str(page.get("html", "") if isinstance(page, dict) else page or "")} for page in pages if str(page.get("html", "") if isinstance(page, dict) else page or "").strip()]


def _client_output_warnings_for_payload(payload):
    """Return compact warning data for the inline editor warning panel."""
    pieces = []
    cover = payload.get("cover") or {}
    pieces.extend(str(cover.get(key, "")) for key in ("trip_title", "trip_subtitle", "trip_dates", "destinations_line"))
    for day in payload.get("days") or []:
        if isinstance(day, dict):
            pieces.extend(str(day.get(key, "")) for key in ("city", "title", "intro", "blocks_html"))
    final_pages = payload.get("final_pages") or {}
    pieces.extend(str(final_pages.get(key, "")) for key in ("whats_included_html", "whats_not_included_html", "whats_not_included_text", "important_travel_notes_text"))
    for page in final_pages.get("whats_included_pages_html") or []:
        if isinstance(page, dict):
            pieces.append(str(page.get("html", "")))
        else:
            pieces.append(str(page or ""))
    findings = scan_client_output("\n".join(piece for piece in pieces if piece))
    compact = []
    seen = set()
    for finding in findings:
        key = (finding.code, finding.excerpt)
        if key in seen:
            continue
        seen.add(key)
        compact.append({"code": finding.code, "excerpt": finding.excerpt})
    return compact[:20]


def _editor_cover_image_payload(parsed_rows, output_edits, key: str, *, pictures_added: bool) -> dict:
    image = resolve_cover_background(parsed_rows, output_edits, key=key, include_image_data=False)
    if not pictures_added:
        image["data_uri"] = ""
        image["auto_data_uri"] = ""
        return image
    if image.get("path"):
        image["data_uri"] = get_image_preview_for_path(image.get("path"))
    if image.get("auto_path"):
        image["auto_data_uri"] = get_image_preview_for_path(image.get("auto_path"))
    return image


def build_visual_editor_payload(parsed_rows, grouped_days, output_edits):
    """Build the editable A4-page payload used by the visual editor component."""
    output_edits = output_edits or {}
    pictures_added = pictures_are_added(output_edits)
    image_matches = select_day_images_with_overrides(grouped_days, output_edits) if pictures_added else {}
    image_warnings = audit_day_image_matches(grouped_days, image_matches, output_edits) if pictures_added else ()
    image_warnings_by_day = {}
    for warning in image_warnings:
        image_warnings_by_day.setdefault(warning.day, []).append({
            "code": warning.code,
            "severity": warning.severity,
            "message": warning.message,
            "path": warning.path,
        })
    payload_days = []
    stored_editor_draft = (output_edits or {}).get("editor_draft") if isinstance(output_edits, dict) else {}
    stored_editor_draft = stored_editor_draft if isinstance(stored_editor_draft, dict) else {}

    for day, rows in grouped_days.items():
        day_edits = (output_edits or {}).get("days", {}).get(day, {})
        typed_day = day_by_id(stored_editor_draft, day)
        group_tour_segment = group_tour_day_from_rows(rows)
        generated_group_tour_city = group_tour_day_city(rows) if group_tour_segment else ""
        generated_group_tour_title = group_tour_day_title(rows) if group_tour_segment else ""
        generated_group_tour_intro = group_tour_day_intro(rows) if group_tour_segment else ""
        city = typed_day.get("city") or day_edits.get("city") or generated_group_tour_city or create_travel_route_label(rows) or get_primary_city(rows)
        if pictures_added:
            match = image_matches.get(day)
            image_path = match.get("path") if match else ""
            preview_data_uri = get_image_preview_for_path(image_path) if image_path else ""
            options = list_replacement_image_options_for_rows(day, rows, limit=12)
            image_obj = {
                "mode": get_day_image_choice(output_edits, day).get("mode", "auto"),
                "path": image_path or "",
                "name": Path(image_path).name if image_path else "",
                "data_uri": preview_data_uri,
                "auto_path": image_path or "",
                "auto_name": Path(image_path).name if image_path else "",
                "auto_data_uri": preview_data_uri,
                "crop_focus": get_day_image_crop_focus(output_edits, day),
                "options": options,
                "warnings": image_warnings_by_day.get(day, []),
            }
        else:
            image_obj = {
                "mode": "pending",
                "path": "",
                "name": "",
                "data_uri": "",
                "auto_path": "",
                "auto_name": "",
                "auto_data_uri": "",
                "crop_focus": "top",
                "options": [],
                "pictures_pending": True,
                "warnings": [],
            }

        # Presence matters here: an intentionally emptied visual-editor block
        # must stay empty instead of falling back to regenerated content.
        typed_blocks_html = first_block_html(typed_day)
        if typed_blocks_html is not None:
            blocks_html = typed_blocks_html
        elif "blocks_html" in day_edits:
            blocks_html = day_edits.get("blocks_html", "")
        else:
            blocks_html = "".join(block["html"] for block in build_day_blocks(rows))

        payload_days.append({
            "day": day,
            "label": typed_day.get("label") or day,
            "date": typed_day.get("date") or get_day_date_text(rows),
            "title": typed_day.get("title") or day_edits.get("title") or generated_group_tour_title or create_day_title(rows),
            "city": city,
            "intro": typed_day.get("intro") or day_edits.get("intro") or generated_group_tour_intro or create_day_intro(rows, detail_level=get_detail_level_name(output_edits)),
            "blocks_html": blocks_html,
            "blocks": typed_day.get("blocks") or [{"block_id": "main", "kind": "day_content", "content_html": blocks_html}],
            "image": image_obj,
        })

    structured_document = build_itinerary_document(parsed_rows, grouped_days)
    generated_inclusions_html = render_inclusion_sections_inner_html(structured_document.inclusions)
    generated_inclusion_page_htmls = render_inclusion_page_inner_htmls(structured_document.inclusions)
    typed_inclusions = section_by_id(stored_editor_draft, "whats_included")
    typed_exclusions = section_by_id(stored_editor_draft, "whats_not_included")
    typed_notes = section_by_id(stored_editor_draft, "important_travel_notes")
    typed_inclusion_pages = [page.get("content_html", "") for page in typed_inclusions.get("pages", []) if isinstance(page, dict)] if typed_inclusions else []
    saved_inclusion_page_htmls = typed_inclusion_pages or output_edits.get("whats_included_pages_html")
    saved_exclusions_html = typed_exclusions.get("content_html") if typed_exclusions else output_edits.get("whats_not_included_html")
    if typed_exclusions and not saved_exclusions_html and typed_exclusions.get("pages"):
        first_page = typed_exclusions.get("pages", [{}])[0]
        saved_exclusions_html = first_page.get("content_html", "") if isinstance(first_page, dict) else ""
    effective_inclusion_page_htmls = _page_html_payload(saved_inclusion_page_htmls or generated_inclusion_page_htmls)
    generated_whats_not_included_text = list_to_text(create_whats_not_included(parsed_rows))
    generated_whats_not_included_html = render_inclusion_sections_inner_html(structured_document.exclusions)
    effective_exclusions_html = saved_exclusions_html or generated_whats_not_included_html
    final_page_source_warnings = (
        *validate_source_aware_html_coverage(
            html_fragments=effective_inclusion_page_htmls,
            sections=structured_document.inclusions,
            page_name="What's included",
            warning_code="edited_inclusions_missing_source_identity",
        ),
        *validate_source_aware_html_coverage(
            html_fragments=effective_exclusions_html,
            sections=structured_document.exclusions,
            page_name="What's not included",
            warning_code="edited_exclusions_missing_source_identity",
        ),
    )
    structured_document.warnings = tuple((*structured_document.warnings, *final_page_source_warnings))
    model_warnings = _compact_model_warnings(structured_document, parsed_rows)
    cover_theme = get_cover_theme(parsed_rows, output_edits, include_image_data=False)
    cover_image = _editor_cover_image_payload(parsed_rows, output_edits, "cover_image", pictures_added=pictures_added)
    summary_image = _editor_cover_image_payload(parsed_rows, output_edits, "summary_image", pictures_added=pictures_added)
    cover_theme["background_path"] = cover_image.get("path", "")
    cover_theme["background_data_uri"] = cover_image.get("data_uri", "")
    cover_theme["background_crop_focus"] = cover_image.get("crop_focus", "top")
    typed_cover = stored_editor_draft.get("cover", {}) if isinstance(stored_editor_draft.get("cover"), dict) else {}
    typed_summary = stored_editor_draft.get("summary", {}) if isinstance(stored_editor_draft.get("summary"), dict) else {}

    payload = {
        "draft_id": output_edits.get("draft_id", ""),
        "meta": {
            "draft_schema_version": 3,
            "source_signature": _source_signature(parsed_rows, grouped_days),
            "day_count": len(payload_days),
        },
        "cover": {
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
            "destinations_line": clean_or_create_cover_route_line(parsed_rows, typed_cover.get("destinations_line") or output_edits.get("destinations_line") or create_destinations_line(parsed_rows)),
        },
        "summary": {
            "trip_glance_title": typed_summary.get("trip_glance_title") or output_edits.get("trip_glance_title", "Your Trip at a Glance"),
            "journey_arc_title": typed_summary.get("journey_arc_title") or output_edits.get("journey_arc_title", "Your Journey Arc"),
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
        },
        "days": payload_days,
        "final_pages": {
            "whats_included_title": typed_inclusions.get("title") if typed_inclusions else output_edits.get("whats_included_title", "What’s included"),
            "whats_not_included_title": typed_exclusions.get("title") if typed_exclusions else output_edits.get("whats_not_included_title", "What’s not included"),
            "important_travel_notes_title": typed_notes.get("title") if typed_notes else output_edits.get("important_travel_notes_title", "Important travel notes"),
            "whats_included_html": output_edits.get("whats_included_html") or generated_inclusions_html,
            "whats_included_pages_html": effective_inclusion_page_htmls,
            "whats_included_text": output_edits.get("whats_included_text", ""),
            "whats_not_included_html": effective_exclusions_html,
            "whats_not_included_text": output_edits.get("whats_not_included_text") or generated_whats_not_included_text,
            "important_travel_notes_text": typed_notes.get("text") if typed_notes else output_edits.get("important_travel_notes_text", ""),
        },
        "issue_flags": output_edits.get("visual_editor_issue_flags", []),
        "workflow": {"pictures_added": pictures_added},
        "model_warnings": model_warnings,
    }
    payload["document_pages"] = build_editor_document_pages(
        payload=payload,
        grouped_days=grouped_days,
        existing_pages=stored_editor_draft.get("document_pages"),
    )
    payload["editor_draft"] = normalise_editable_draft(payload)
    output_warnings = _client_output_warnings_for_payload(payload)
    for warning in model_warnings:
        output_warnings.append({
            "code": warning.get("code", "model_warning"),
            "excerpt": warning.get("message", "Structured model warning"),
            "message": warning.get("message", "Structured model warning"),
            "page_label": warning.get("page_label", "Structured itinerary"),
            "source_row_ids": warning.get("source_row_ids", []),
        })
    for warning in image_warnings:
        output_warnings.append({
            "code": warning.code,
            "excerpt": warning.message,
        })
    payload["client_output_warnings"] = output_warnings[:30]
    if isinstance(output_edits, dict):
        # Keep the latest warning payload available for the persistent QA report.
        # This is tiny metadata only; it avoids rebuilding the visual editor model
        # during QA-report export.
        output_edits["latest_client_output_warnings"] = payload["client_output_warnings"]
    return payload


