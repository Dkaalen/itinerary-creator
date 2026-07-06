"""Build and persist the first HTML preview after itinerary generation."""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any

from app_modules.itinerary_html import build_itinerary_html_from_context
from app_modules.itinerary_render_context import build_itinerary_render_context
from app_modules.performance_telemetry import measure_timing
from app_modules.render_context_cache import store_render_context
from app_modules.parse_workflow import get_overflow_warnings
from itinerary_generation.common import group_rows_by_day
from ui.export_files import save_html_file
from ui.output_edits import apply_output_edits
from ui.render_cache import make_render_signature


@dataclass(frozen=True)
class GenerationPreviewArtifact:
    """HTML preview artifact and derived grouping for generated rows."""

    html: str
    html_path: str
    signature: str
    overflow_warnings: list[str]


def build_generation_preview_artifact(
    state: MutableMapping[str, Any],
    *,
    parsed_rows: list[dict],
    output_edits: dict[str, Any],
) -> GenerationPreviewArtifact:
    """Build HTML, cache render context, and save the generated preview file."""

    edited_rows = apply_output_edits(parsed_rows, output_edits)
    edited_grouped_days = group_rows_by_day(edited_rows)
    with measure_timing(state, "build_render_context", count=len(edited_rows or [])):
        render_context = build_itinerary_render_context(edited_rows, edited_grouped_days, output_edits)
    html = build_itinerary_html_from_context(render_context)
    signature = make_render_signature(parsed_rows, output_edits)
    store_render_context(state, signature=signature, context=render_context)
    html_path = save_html_file(html)
    return GenerationPreviewArtifact(
        html=html,
        html_path=html_path,
        signature=signature,
        overflow_warnings=get_overflow_warnings(edited_grouped_days),
    )


__all__ = ["GenerationPreviewArtifact", "build_generation_preview_artifact"]
