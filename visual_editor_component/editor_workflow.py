"""Visual editor payload and save workflow."""

import hashlib
import json
from pathlib import Path

import streamlit as st

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
from itinerary_generation.date_resolver import get_day_date_text, get_trip_date_range_text
from itinerary_generation.inclusions import create_whats_not_included
from itinerary_generation.structured_builder import build_itinerary_document
from itinerary_generation.structured_html_audit import validate_source_aware_html_coverage
from itinerary_generation.transport_safety import scan_client_output
from itinerary_generation.summaries import create_journey_arc, create_trip_glance, sanitize_journey_arc_experience
from images.app_image_selection import (
    get_day_image_choice,
    get_day_image_crop_focus,
    get_image_preview_for_path,
    list_replacement_image_options_for_rows,
    audit_day_image_matches,
    normalize_crop_focus,
    save_data_uri_day_image,
    select_day_images_with_overrides,
)
from ui.day_pages import render_inclusion_sections_inner_html, render_inclusion_page_inner_htmls
from ui.day_blocks import build_day_blocks
from ui.render_helpers import get_detail_level_name, list_to_text
from ui.picture_workflow import pictures_are_added
from ui.editor_sanitizer import clean_visual_editor_html, normalize_final_list_html
from itinerary_generation.editable_draft import (
    day_by_id,
    first_block_html,
    merge_editable_drafts,
    mirror_draft_to_legacy_output_edits,
    normalise_editable_draft,
    section_by_id,
)
from visual_editor_component.editor_bridge import render_visual_page_editor



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


def _normalize_route_edit(value):
    """Normalize editable cover-route text back to a single separator-delimited line."""
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", " · ")
    parts = [part.strip() for part in text.split("·") if part.strip()]
    return " · ".join(parts)


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
        city = typed_day.get("city") or day_edits.get("city") or create_travel_route_label(rows) or get_primary_city(rows)
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
            "title": typed_day.get("title") or day_edits.get("title") or create_day_title(rows),
            "city": city,
            "intro": typed_day.get("intro") or day_edits.get("intro") or create_day_intro(rows, detail_level=get_detail_level_name(output_edits)),
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
    cover_theme = get_cover_theme(parsed_rows, output_edits, include_image_data=pictures_added)
    if pictures_added and cover_theme.get("background_path"):
        # The editor needs only a screen preview. Keep the PDF/export path
        # pointing at the original file, but avoid sending the full cover image
        # through the Streamlit component payload.
        cover_theme["background_data_uri"] = get_image_preview_for_path(cover_theme.get("background_path"))
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
            "cover_season": cover_theme.get("season", "summer"),
            "cover_background_data_uri": cover_theme.get("background_data_uri", ""),
            "cover_ink": cover_theme.get("ink", "#1f3446"),
            "cover_muted": cover_theme.get("muted", "#7b746c"),
            "cover_accent": cover_theme.get("accent", "#b89555"),
            "trip_title": typed_cover.get("trip_title") or output_edits.get("trip_title", create_trip_title(parsed_rows, grouped_days)),
            "trip_subtitle": typed_cover.get("trip_subtitle") or output_edits.get("trip_subtitle", create_trip_subtitle(parsed_rows, grouped_days)),
            "trip_dates": typed_cover.get("trip_dates") or output_edits.get("trip_dates") or get_trip_date_range_text(parsed_rows),
            "destinations_line": clean_or_create_cover_route_line(parsed_rows, typed_cover.get("destinations_line") or output_edits.get("destinations_line") or create_destinations_line(parsed_rows)),
        },
        "summary": {
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


def _decode_visual_editor_result(result):
    """Decode visual editor payloads, including export-commit wrappers."""
    data = json.loads(result) if isinstance(result, str) else result
    if isinstance(data, dict) and "payload" in data and "commit_nonce" in data:
        return data.get("payload") or {}, str(data.get("commit_nonce") or "")
    return data, ""




def _sanitize_editor_draft(editor_draft):
    """Clean typed editor draft values before storing/mirroring them."""
    if not isinstance(editor_draft, dict):
        return {}
    cleaned = json.loads(json.dumps(editor_draft))
    cover = cleaned.get("cover") if isinstance(cleaned.get("cover"), dict) else {}
    for key, value in list(cover.items()):
        text = str(value or "").strip()
        cover[key] = _normalize_route_edit(text) if key == "destinations_line" else text
    cleaned["cover"] = cover

    for day in cleaned.get("days") or []:
        if not isinstance(day, dict):
            continue
        for key in ("title", "city", "intro", "label", "date"):
            if key in day:
                day[key] = str(day.get(key, "")).strip()
        for block in day.get("blocks") or []:
            if isinstance(block, dict):
                block["content_html"] = clean_visual_editor_html(block.get("content_html", block.get("html", "")) or "")

    for section in cleaned.get("final_sections") or []:
        if not isinstance(section, dict):
            continue
        section_id = str(section.get("section_id", ""))
        for page in section.get("pages") or []:
            if not isinstance(page, dict):
                continue
            html = page.get("content_html", page.get("html", "")) or ""
            page["content_html"] = normalize_final_list_html(html) if section_id == "whats_not_included" else clean_visual_editor_html(html)
        if "content_html" in section:
            html = section.get("content_html", "") or ""
            section["content_html"] = normalize_final_list_html(html) if section_id == "whats_not_included" else clean_visual_editor_html(html)
        if "text" in section:
            section["text"] = str(section.get("text", "")).strip()
    return cleaned


def _stable_output_edits_snapshot(output_edits):
    return json.dumps(output_edits or {}, ensure_ascii=False, sort_keys=True, default=str)


def apply_visual_editor_result(result, output_edits, mark_dirty=None):
    """Persist visual editor edits into the normal output_edits structure."""
    if not result:
        return False
    before_snapshot = _stable_output_edits_snapshot(output_edits)
    try:
        data, commit_nonce = _decode_visual_editor_result(result)
    except Exception:
        st.warning("Visual editor edits could not be read. Please try saving again.")
        return False
    if not isinstance(data, dict):
        return False

    cover = data.get("cover", {}) or {}
    for key in ["cover_kicker", "trip_title", "trip_subtitle", "trip_dates", "destinations_line"]:
        if key in cover:
            value = str(cover.get(key, "")).strip()
            output_edits[key] = _normalize_route_edit(value) if key == "destinations_line" else value

    workflow = data.get("workflow", {}) or {}
    if isinstance(workflow, dict) and "pictures_added" in workflow:
        output_edits["pictures_added"] = bool(workflow.get("pictures_added"))

    summary = data.get("summary", {}) or {}
    if isinstance(summary.get("trip_glance"), dict):
        output_edits["trip_glance"] = {
            str(key).strip(): str(value).strip()
            for key, value in summary.get("trip_glance", {}).items()
            if str(key).strip()
        }
    if isinstance(summary.get("journey_arc"), list):
        output_edits["journey_arc"] = [
            {
                "chapter": str(row.get("chapter", "")).strip(),
                "days": str(row.get("days", "")).strip(),
                "experience": str(row.get("experience", "")).strip(),
            }
            for row in summary.get("journey_arc", [])
            if isinstance(row, dict)
        ]

    day_payloads = data.get("days", []) or []
    for day_payload in day_payloads:
        day = day_payload.get("day")
        if not day:
            continue
        day_edits = output_edits.setdefault("days", {}).setdefault(day, {})
        for key in ["title", "city", "intro"]:
            if key in day_payload:
                day_edits[key] = str(day_payload.get(key, "")).strip()
        if "blocks_html" in day_payload:
            # A present blocks_html field is an explicit editor decision. Store
            # even an empty string so clearing a day block does not regenerate
            # the old generated travel/activity content during PDF export.
            day_edits["blocks_html"] = clean_visual_editor_html(day_payload.get("blocks_html", ""))

        image_payload = day_payload.get("image") or {}
        if image_payload:
            choice = get_day_image_choice(output_edits, day)
            mode = str(image_payload.get("mode") or choice.get("mode", "auto")).strip().lower()
            if mode not in {"auto", "manual", "none"}:
                mode = "auto"
            choice["mode"] = mode
            choice["crop_focus"] = normalize_crop_focus(image_payload.get("crop_focus", choice.get("crop_focus", "top")))

            upload = image_payload.get("upload") or {}
            if mode == "manual" and upload.get("data_uri"):
                saved_path = save_data_uri_day_image(
                    upload.get("data_uri", ""),
                    upload.get("filename", "uploaded_image.jpg"),
                    day_edits.get("city") or day_payload.get("city", ""),
                    upload.get("season", "Summer"),
                    upload.get("label", ""),
                )
                choice["path"] = saved_path or str(image_payload.get("path") or choice.get("path", "")).strip()
            elif mode == "manual":
                choice["path"] = str(image_payload.get("path") or choice.get("path", "")).strip()
            elif mode in {"auto", "none"}:
                choice["path"] = ""

    final_pages = data.get("final_pages", {}) or {}
    if "whats_included_pages_html" in final_pages:
        page_values = final_pages.get("whats_included_pages_html") or []
        cleaned_pages = []
        if isinstance(page_values, list):
            for page_value in page_values:
                if isinstance(page_value, dict):
                    page_html = page_value.get("html", "")
                else:
                    page_html = page_value
                cleaned = clean_visual_editor_html(page_html or "")
                if cleaned:
                    cleaned_pages.append(cleaned)
        # A present page list is an explicit editor decision. Persist it even
        # when the user deleted every page, using a blank sentinel so the
        # generated inclusion pages do not silently reappear.
        output_edits["whats_included_pages_html"] = cleaned_pages or [""]
        output_edits["whats_included_html"] = ""
        output_edits["whats_included_text"] = ""
    elif "whats_included_html" in final_pages:
        output_edits["whats_included_html"] = clean_visual_editor_html(final_pages.get("whats_included_html", ""))
        output_edits.pop("whats_included_pages_html", None)
        output_edits["whats_included_text"] = ""
    if "whats_not_included_html" in final_pages:
        output_edits["whats_not_included_html"] = normalize_final_list_html(final_pages.get("whats_not_included_html", ""))
        # The structured HTML list is now the saved source for this page. Keep
        # the old text key empty so preview/PDF do not flatten it back into a
        # paragraph during a later rebuild.
        output_edits["whats_not_included_text"] = ""

    for key in ["whats_included_text", "whats_not_included_text", "important_travel_notes_text"]:
        if key in final_pages and key != "whats_included_text":
            # Do not let legacy text fallback overwrite an explicitly edited
            # structured exclusion page in the same payload.
            if key == "whats_not_included_text" and output_edits.get("whats_not_included_html"):
                continue
            output_edits[key] = str(final_pages.get(key, "")).strip()

    if "editor_draft" in data:
        incoming_draft = normalise_editable_draft(data)
        existing_draft = output_edits.get("editor_draft") if isinstance(output_edits.get("editor_draft"), dict) else {}
        editor_draft = _sanitize_editor_draft(merge_editable_drafts(existing_draft, incoming_draft))
        mirror_draft_to_legacy_output_edits(output_edits, editor_draft)

    if isinstance(data.get("issue_flags"), list):
        cleaned_flags = []
        for flag in data.get("issue_flags") or []:
            if not isinstance(flag, dict):
                continue
            key = str(flag.get("key", "")).strip()
            corrected = str(flag.get("corrected", "")).strip()
            if not key and not corrected:
                continue
            cleaned_flags.append({
                "key": key,
                "label": str(flag.get("label", "")).strip(),
                "original": str(flag.get("original", "")).strip(),
                "corrected": corrected,
            })
        if cleaned_flags:
            existing = output_edits.get("visual_editor_issue_flags") if isinstance(output_edits.get("visual_editor_issue_flags"), list) else []
            seen = {(str(item.get("key", "")), str(item.get("corrected", ""))) for item in existing if isinstance(item, dict)}
            for flag in cleaned_flags:
                dedupe_key = (flag["key"], flag["corrected"])
                if dedupe_key not in seen:
                    existing.append(flag)
                    seen.add(dedupe_key)
            output_edits["visual_editor_issue_flags"] = existing

    if commit_nonce:
        st.session_state["_visual_editor_last_applied_commit_nonce"] = commit_nonce

    after_snapshot = _stable_output_edits_snapshot(output_edits)
    st.session_state["_visual_editor_last_result_changed"] = before_snapshot != after_snapshot
    if mark_dirty and before_snapshot != after_snapshot:
        mark_dirty()
    return True


def render_visual_editor(parsed_rows, grouped_days, output_edits, rebuild_preview=None, mark_dirty=None):
    """Render and process the direct editable A4-page editor.

    Returns True only when a saved editor payload was applied. The app can then
    skip any additional rebuild based on the pre-save rows from the same rerun.
    """
    payload = build_visual_editor_payload(parsed_rows, grouped_days, output_edits)
    commit_nonce = st.session_state.get("_visual_editor_commit_nonce")
    result = render_visual_page_editor(payload, key="visual_page_editor", commit_nonce=commit_nonce)
    if result and result != st.session_state.get("_last_visual_editor_result"):
        st.session_state["_last_visual_editor_result"] = result
        if apply_visual_editor_result(result, output_edits, mark_dirty=mark_dirty):
            if rebuild_preview:
                rebuild_preview(mark_pdf_dirty=True)
            applied_nonce = st.session_state.get("_visual_editor_last_applied_commit_nonce")
            if applied_nonce and str(applied_nonce) == str(st.session_state.get("_pdf_after_visual_edit_commit_nonce", "")):
                st.session_state["_visual_editor_export_commit_ready"] = True
            elif applied_nonce and str(applied_nonce) == str(st.session_state.get("_add_pictures_after_visual_edit_commit_nonce", "")):
                st.session_state["_visual_editor_add_pictures_commit_ready"] = True
            else:
                if st.session_state.get("_visual_editor_last_result_changed"):
                    st.success("Edits saved to preview and PDF export.")
            return True
    return False
