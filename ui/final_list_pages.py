"""Simple final list page rendering."""

from __future__ import annotations

from ui.render_helpers import esc, normalize_list, render_list_items


def render_split_list_pages(title, items, items_per_page=24):
    html_text = ""
    clean_items = normalize_list(items)

    if not clean_items:
        return ""

    for start in range(0, len(clean_items), items_per_page):
        chunk = clean_items[start:start + items_per_page]
        continued = "" if start == 0 else " continued"

        html_text += f"""
        <div class="a4-page final-list-page">
            <div class="final-page-title">{esc(title)}{continued}</div>
            {render_list_items(chunk, class_name="final-list")}
        </div>
        """

    return html_text


