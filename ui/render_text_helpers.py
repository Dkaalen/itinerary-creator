"""Generic text and list helpers for UI rendering."""

from __future__ import annotations

import html


def get_detail_level_name(output_edits=None):
    """Return the fixed rich descriptive level used by the current app output."""
    return "Rich descriptive"


def esc(value):
    return html.escape(str(value or ""), quote=True)


def clean_space(value):
    """Small local whitespace normalizer used by UI/helper functions.

    The parser has its own clean_space helper, but app.py should not depend on
    private parser helpers at runtime. Keeping this local prevents UI helper
    functions from raising NameError when they clean pickup/drop-off text.
    """
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def normalize_list(items):
    if not items:
        return []

    if isinstance(items, list):
        return [str(item).strip() for item in items if item and str(item).strip()]

    if isinstance(items, str):
        return [item.strip() for item in items.split(",") if item.strip()]

    return []


def list_to_text(items):
    return "\n".join(normalize_list(items))


def text_to_list(value):
    if not value:
        return []

    clean_items = []

    for line in str(value).splitlines():
        item = line.strip()
        item = item.lstrip("•").lstrip("-").strip()

        if item:
            clean_items.append(item)

    return clean_items


def render_list_items(items, class_name="detail-list"):
    clean_items = normalize_list(items)

    if not clean_items:
        return ""

    html_text = f'<ul class="{esc(class_name)}">'

    for item in clean_items:
        html_text += f"<li>{esc(item)}</li>"

    html_text += "</ul>"

    return html_text
