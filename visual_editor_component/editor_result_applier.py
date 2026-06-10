"""Apply visual editor save payloads to output_edits."""

import json

import streamlit as st

from images.app_image_selection import (
    get_day_image_choice,
    normalize_crop_focus,
    save_data_uri_day_image,
)
from itinerary_generation.editable_draft import (
    merge_editable_drafts,
    mirror_draft_to_legacy_output_edits,
    normalise_editable_draft,
)
from ui.editor_sanitizer import clean_visual_editor_html, normalize_final_list_html
from itinerary_generation.draft_autosave import save_autosave_payload
from visual_editor_component.editor_status import autosave_status


def _normalize_route_edit(value):
    """Normalize editable cover-route text back to a single separator-delimited line."""
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\n", " · ")
    parts = [part.strip() for part in text.split("·") if part.strip()]
    return " · ".join(parts)


def _decode_visual_editor_result(result):
    """Decode visual editor payloads, including export/autosave wrappers."""
    data = json.loads(result) if isinstance(result, str) else result
    if isinstance(data, dict) and "payload" in data and ("commit_nonce" in data or "autosave" in data):
        commit_nonce = str(data.get("commit_nonce") or "")
        return data.get("payload") or {}, commit_nonce, bool(data.get("autosave"))
    return data, "", False


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
        data, commit_nonce, is_autosave = _decode_visual_editor_result(result)
    except Exception:
        st.warning("Visual editor edits could not be read. Please try saving again.")
        return False
    if not isinstance(data, dict):
        return False

    incoming_signature = str((data.get("meta") or {}).get("source_signature") or "").strip()
    expected_signature = str(st.session_state.get("_visual_editor_current_source_signature") or "").strip()
    if incoming_signature and expected_signature and incoming_signature != expected_signature:
        st.session_state["_visual_editor_last_result_changed"] = False
        st.session_state["_visual_editor_last_result_was_autosave"] = bool(is_autosave)
        return False

    st.session_state["_visual_editor_last_result_was_autosave"] = bool(is_autosave)

    if is_autosave:
        saved_info = save_autosave_payload(data, draft_id=(output_edits or {}).get("draft_id"))
        autosave_status(saved_info)

    cover = data.get("cover", {}) or {}
    for key in ["cover_kicker", "trip_title", "trip_subtitle", "trip_dates", "destinations_line"]:
        if key in cover:
            value = str(cover.get(key, "")).strip()
            output_edits[key] = _normalize_route_edit(value) if key == "destinations_line" else value

    workflow = data.get("workflow", {}) or {}
    if isinstance(workflow, dict) and "pictures_added" in workflow:
        # Visual-editor payloads can be stale across the text → picture-stage
        # transition. The app workflow action is authoritative for disabling
        # pictures; editor payloads may promote False → True, but must not
        # downgrade True → False after pictures have been added.
        incoming_pictures_added = bool(workflow.get("pictures_added"))
        output_edits["pictures_added"] = bool(output_edits.get("pictures_added")) or incoming_pictures_added

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


