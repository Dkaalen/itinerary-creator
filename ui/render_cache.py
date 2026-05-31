"""Small cache-key helpers for preview/PDF rendering.

The Streamlit app reruns often. These helpers give the UI a stable way to
recognise when the itinerary content has actually changed, so expensive HTML
and PDF work can be skipped on ordinary reruns.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _json_default(value: Any) -> str:
    """Return a deterministic JSON fallback for non-plain values."""
    if isinstance(value, Path):
        return str(value)
    return str(value)


def make_render_signature(parsed_rows: Any, output_edits: Any) -> str:
    """Create a stable signature for the current itinerary rendering state."""
    payload = {
        "parsed_rows": parsed_rows or [],
        "output_edits": output_edits or {},
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=_json_default,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
