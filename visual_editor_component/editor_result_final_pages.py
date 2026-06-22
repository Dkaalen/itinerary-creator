"""Apply visual-editor final-section payload fields."""

from ui.editor_sanitizer import clean_visual_editor_html, normalize_final_list_html


def apply_final_pages_payload(data, output_edits):
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
