from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


def is_debug_mode(state: Mapping[str, Any] | None = None) -> bool:
    """Return whether diagnostic/developer UI is explicitly enabled."""

    if state and bool(state.get("debug_mode_enabled")):
        return True
    return os.getenv("ITINERARY_DEBUG_UI", "").strip().lower() in {"1", "true", "yes", "on"}
