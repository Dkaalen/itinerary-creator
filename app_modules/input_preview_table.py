"""Structured supplier-input preview for the input workspace."""

from __future__ import annotations

from collections.abc import MutableMapping
from html import escape
from typing import Any

import streamlit as st

import diagnostics
from app_modules.parse_workflow import parse_and_normalize_itinerary
from app_modules.performance_telemetry import measure_timing, record_trace, telemetry_is_active
from app_modules.session_state_keys import OPEN_PROJECT_BROWSER_VISIBLE_KEY
from app_modules.supplier_preview_cache import (
    SupplierRowsPreview,
    cached_supplier_rows_preview,
    clear_supplier_preview_cache,
    remember_supplier_rows_preview,
)

_PREVIEW_LIMIT = 18


def render_supplier_rows_preview(raw_text: str) -> SupplierRowsPreview | None:
    """Render and return one session-cached parse preview for pasted supplier rows."""

    source_text = str(raw_text or "")
    text = source_text.strip()
    if not text:
        return None
    session = st.session_state
    cached = cached_supplier_rows_preview(session, source_text)
    if cached is not None:
        _record_cache_trace(session, "supplier_preview_cache_hit", source_text, cached)
        _render_preview(cached)
        return cached

    if bool(session.get(OPEN_PROJECT_BROWSER_VISIBLE_KEY)):
        if telemetry_is_active(session):
            record_trace(
                session,
                "supplier_preview_deferred",
                source_characters=len(source_text),
                reason="project_explorer_open",
            )
        st.caption("The parsed preview will update after Project Explorer is closed.")
        return None

    telemetry_state = session if telemetry_is_active(session) else None
    try:
        with diagnostics.capture_warnings() as captured_warnings:
            with measure_timing(telemetry_state, "supplier_preview_parse"):
                rows = parse_and_normalize_itinerary(text, state=telemetry_state)
        parser_diagnostics = [dict(item) for item in captured_warnings]
    except Exception as exc:
        if telemetry_state is not None:
            record_trace(
                telemetry_state,
                "supplier_preview_failed",
                source_characters=len(source_text),
                error_type=type(exc).__name__,
            )
        st.caption("Preview unavailable. Generate will still validate the pasted rows.")
        return None
    preview = remember_supplier_rows_preview(
        session,
        source_text,
        rows,
        parser_diagnostics=parser_diagnostics,
    )
    if preview is None:
        return None
    _record_cache_trace(session, "supplier_preview_cache_miss", source_text, preview)
    _render_preview(preview)
    return preview


def _render_preview(preview: SupplierRowsPreview) -> None:
    if not preview.rows:
        st.caption("No itinerary rows detected yet.")
        return
    st.html(_preview_html(list(preview.rows)))


def _record_cache_trace(
    state: MutableMapping[str, Any],
    event: str,
    text: str,
    preview: SupplierRowsPreview,
) -> None:
    if telemetry_is_active(state):
        record_trace(
            state,
            event,
            source_characters=len(text),
            row_count=len(preview.rows),
        )


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


__all__ = ["SupplierRowsPreview", "clear_supplier_preview_cache", "render_supplier_rows_preview"]
