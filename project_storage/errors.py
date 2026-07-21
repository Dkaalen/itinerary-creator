"""UI-safe project storage error helpers."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from app_modules.session_transitions import clear_failed_save, record_failed_save

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


def record_storage_error(state: MutableMapping[str, Any], exc: Exception, *, action: str = "storage") -> None:
    """Store user-safe and technical storage errors separately."""

    record_failed_save(
        state,
        user_message=storage_user_message(action),
        technical_detail=_technical_summary(exc),
    )


def clear_storage_error(state: MutableMapping[str, Any]) -> None:
    """Clear the last storage failure markers."""

    clear_failed_save(state)


def _technical_summary(exc: Exception) -> str:
    text = " ".join(str(exc or "").split())
    return text[:500]
