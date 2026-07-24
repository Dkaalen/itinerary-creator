"""Pure project-storage error messages and detail normalization."""

from __future__ import annotations

_GENERIC_MESSAGES = {
    "list": "Cloud projects could not be loaded right now.",
    "open": "Cloud project could not be opened right now.",
    "save": "Project was not saved to Supabase. Try again before closing this session.",
    "delete": "Cloud project could not be deleted right now.",
    "files": "Calculator files could not be loaded right now.",
    "download": "Calculator file could not be prepared right now.",
    "storage": "Supabase storage is temporarily unavailable.",
}


def storage_user_message(action: str = "storage") -> str:
    """Return a short, non-sensitive storage error for UI surfaces."""

    return _GENERIC_MESSAGES.get(str(action or "storage"), _GENERIC_MESSAGES["storage"])


def storage_error_detail(exc: Exception) -> str:
    """Return a bounded technical error detail for diagnostics and state logs."""

    return " ".join(str(exc or "").split())[:500]
