"""Stable PDF export identity for current preview and export-only state."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

# These fields can change the PDF without necessarily changing the cached HTML
# preview bytes at the exact same time.  Keep this list narrow and export-owned:
# row/text changes are already represented by the preview signature.
_EXPORT_ONLY_OUTPUT_EDIT_KEYS = (
    "day_images",
    "cover_image",
    "summary_image",
    "pictures_added",
    "output_brand",
    "color_preset",
    "presentation_language",
    "day_page_layout",
    "detail_level",
    "tone_preset",
)


def _json_default(value: Any) -> str:
    return str(value)


def export_state_for_signature(state: Mapping[str, Any]) -> dict[str, Any]:
    """Return the minimal export-only state that invalidates cached PDF bytes."""

    edits = state.get("output_edits") if isinstance(state.get("output_edits"), Mapping) else {}
    return {key: edits.get(key) for key in _EXPORT_ONLY_OUTPUT_EDIT_KEYS}


def export_signature_for_state(state: Mapping[str, Any]) -> str | None:
    """Return the stable current PDF identity, or None until preview exists."""

    preview_signature = state.get("preview_signature")
    if not preview_signature:
        return None
    payload = {
        "preview_signature": str(preview_signature),
        "export_state": export_state_for_signature(state),
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=_json_default, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8", errors="ignore")).hexdigest()[:32]


__all__ = ["export_signature_for_state", "export_state_for_signature"]
