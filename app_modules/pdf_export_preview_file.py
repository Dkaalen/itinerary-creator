"""Preview-file helpers used by the PDF export workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def current_preview_html_path(state: Mapping[str, Any]) -> Path | None:
    """Return the current preview HTML file path when one is recorded."""

    html_path = state.get("html_path")
    return Path(html_path) if html_path else None


def preview_file_exists(state: Mapping[str, Any]) -> bool:
    """Return whether the state points at an existing preview HTML file."""

    path = current_preview_html_path(state)
    return bool(path and path.exists())


__all__ = ["current_preview_html_path", "preview_file_exists"]
