"""Structured supplier-input preview for the input workspace."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from app_modules.parse_workflow import parse_and_normalize_itinerary

_PREVIEW_LIMIT = 18


def render_supplier_rows_preview(raw_text: str) -> None:
    """Render a compact, read-only parse preview for pasted supplier rows."""

    text = str(raw_text or "").strip()
    if not text:
        return
    try:
        rows = parse_and_normalize_itinerary(text)
    except Exception:
        st.caption("Preview unavailable. Generate will still validate the pasted rows.")
        return
    if not rows:
        st.caption("No itinerary rows detected yet.")
        return

    st.html(_preview_html(rows))


def _preview_html(rows: list[dict[str, Any]]) -> str:
    visible_rows = rows[:_PREVIEW_LIMIT]
    hidden_count = max(0, len(rows) - len(visible_rows))
    body = "".join(_row_html(row) for row in visible_rows)
    hidden = f'<div class="supplier-preview-more">+ {hidden_count} more rows</div>' if hidden_count else ""
    return f"""
    <section class="supplier-preview-panel" aria-label="Parsed supplier rows preview">
      <div class="supplier-preview-header">
        <span>Parsed rows preview</span>
        <strong>{len(rows)} rows</strong>
      </div>
      <div class="supplier-preview-scroll">
        <table class="supplier-preview-table">
          <thead>
            <tr>
              <th>Day</th>
              <th>Type</th>
              <th>Date</th>
              <th>City</th>
              <th>Travel element</th>
            </tr>
          </thead>
          <tbody>{body}</tbody>
        </table>
      </div>
      {hidden}
    </section>
    """


def _row_html(row: dict[str, Any]) -> str:
    day = _cell(row.get("day") or row.get("day_label"))
    row_type = _cell(row.get("type") or row.get("effective_type"))
    date = _cell(row.get("date") or row.get("start_date") or row.get("from_date"))
    city = _cell(row.get("city") or row.get("destination") or row.get("location"))
    element = _cell(row.get("title") or row.get("travel_element") or row.get("description") or row.get("details"))
    return f"<tr><td>{day}</td><td>{row_type}</td><td>{date}</td><td>{city}</td><td>{element}</td></tr>"


def _cell(value: object) -> str:
    text = " ".join(str(value or "").split())
    return escape(text[:180])
