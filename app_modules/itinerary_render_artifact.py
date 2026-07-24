"""Canonical construction and persistence for itinerary preview artifacts.

Every workflow that needs the current prepared itinerary must build it through
this module.  Workflow modules remain responsible for transitions and PDF
invalidation; this module owns the deterministic render artifact itself.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app_modules.itinerary_html import build_itinerary_html_from_context
from app_modules.itinerary_render_context import ItineraryRenderContext, build_itinerary_render_context
from app_modules.parse_workflow import get_overflow_warnings
from app_modules.performance_telemetry import measure_timing
from app_modules.render_context_cache import store_render_context
from app_modules.session_state_keys import (
    HTML_PATH_KEY,
    ITINERARY_HTML_KEY,
    PREVIEW_SIGNATURE_KEY,
)
from itinerary_generation.common import group_rows_by_day
from ui.export_files import save_html_file
from ui.output_edits import apply_output_edits
from ui.render_cache import make_render_signature


@dataclass(frozen=True, slots=True)
class ItineraryRenderArtifact:
    """One prepared itinerary shared by preview, editor, restore, and PDF."""

    edited_rows: list[dict[str, Any]]
    grouped_days: dict[str, list[dict[str, Any]]]
    render_context: ItineraryRenderContext
    html: str
    signature: str
    overflow_warnings: list[str]


def build_itinerary_render_artifact(
    parsed_rows: list[dict[str, Any]],
    output_edits: dict[str, Any],
    *,
    telemetry_state: MutableMapping[str, Any] | None = None,
) -> ItineraryRenderArtifact:
    """Build the complete deterministic artifact for rows and output edits."""

    edited_rows = apply_output_edits(parsed_rows, output_edits)
    grouped_days = group_rows_by_day(edited_rows)
    with measure_timing(
        telemetry_state,
        "build_render_context",
        count=len(edited_rows or []),
    ):
        render_context = build_itinerary_render_context(edited_rows, grouped_days, output_edits)
    return ItineraryRenderArtifact(
        edited_rows=edited_rows,
        grouped_days=grouped_days,
        render_context=render_context,
        html=build_itinerary_html_from_context(render_context),
        signature=make_render_signature(parsed_rows, output_edits),
        overflow_warnings=get_overflow_warnings(grouped_days),
    )


def persist_itinerary_render_artifact(
    state: MutableMapping[str, Any],
    artifact: ItineraryRenderArtifact,
    *,
    save_html: bool,
    update_preview_state: bool = True,
    cache_signature: str | None = None,
) -> Path | None:
    """Store a prepared artifact without taking ownership of workflow transitions."""

    signature = str(cache_signature or artifact.signature)
    store_render_context(state, signature=signature, context=artifact.render_context)

    if not update_preview_state:
        return None

    state[ITINERARY_HTML_KEY] = artifact.html
    state[PREVIEW_SIGNATURE_KEY] = artifact.signature
    html_path: Path | None = None
    if save_html:
        html_path = save_html_file(artifact.html)
        state[HTML_PATH_KEY] = html_path
    return html_path


def build_and_persist_itinerary_render_artifact(
    state: MutableMapping[str, Any],
    *,
    parsed_rows: list[dict[str, Any]],
    output_edits: dict[str, Any],
    save_html: bool,
    telemetry_state: MutableMapping[str, Any] | None = None,
    update_preview_state: bool = True,
    cache_signature: str | None = None,
) -> ItineraryRenderArtifact:
    """Build and store the canonical artifact through one supported path."""

    artifact = build_itinerary_render_artifact(
        parsed_rows,
        output_edits,
        telemetry_state=telemetry_state,
    )
    persist_itinerary_render_artifact(
        state,
        artifact,
        save_html=save_html,
        update_preview_state=update_preview_state,
        cache_signature=cache_signature,
    )
    return artifact


__all__ = [
    "ItineraryRenderArtifact",
    "build_and_persist_itinerary_render_artifact",
    "build_itinerary_render_artifact",
    "persist_itinerary_render_artifact",
]
