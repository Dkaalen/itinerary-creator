"""Lazy Python bridge for the browser-owned Project Explorer table."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

_COMPONENT_DIR = Path(__file__).resolve().parent / "frontend"
_project_explorer: Callable[..., dict[str, Any] | None] | None = None


def _project_explorer_component() -> Callable[..., dict[str, Any] | None]:
    """Declare the component only when Project Explorer is visible."""

    global _project_explorer
    if _project_explorer is None:
        import streamlit.components.v1 as components

        _project_explorer = components.declare_component(
            "project_explorer_table",
            path=str(_COMPONENT_DIR),
        )
    return _project_explorer


def render_project_explorer_table(
    payload: dict[str, Any],
    *,
    key: str = "cloud_project_explorer_table",
) -> dict[str, Any] | None:
    """Render the client-owned table and return explicit user actions only."""

    component = _project_explorer_component()
    return component(payload=dict(payload or {}), key=key, default=None)


__all__ = ["render_project_explorer_table"]
