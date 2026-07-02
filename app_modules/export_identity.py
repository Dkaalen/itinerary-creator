"""Stable PDF export identity for current preview and image state."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

_IMAGE_EXPORT_KEYS = (
    "day_images",
    "cover_image",
    "summary_image",
    "pictures_added",
    "output_brand",
    "color_preset",
    "presentation_language",
)


def _json_default(value: Any) -> str:
    return str(value)


def export_signature_for_state(state: Mapping[str, Any]) -> str | None:
    """Return the stable current PDF identity, or None until preview exists."""

    preview_signature = state.get("preview_signature")
    if not preview_signature:
        return None
    edits = state.get("output_edits") if isinstance(state.get("output_edits"), Mapping) else {}
    payload = {
        "preview_signature": str(preview_signature),
        "image_export_state": {key: edits.get(key) for key in _IMAGE_EXPORT_KEYS},
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=_json_default, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8", errors="ignore")).hexdigest()[:32]


__all__ = ["export_signature_for_state"]
