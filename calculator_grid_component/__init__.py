"""Lazy Python bridge for the browser-side calculator grid component."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

_COMPONENT_DIR = Path(__file__).resolve().parent / "frontend"
_calculator_grid: Callable[..., str | None] | None = None


def _calculator_grid_component() -> Callable[..., str | None]:
    """Declare the Streamlit component only when the Calculator is rendered."""

    global _calculator_grid
    if _calculator_grid is None:
        import streamlit.components.v1 as components

        _calculator_grid = components.declare_component(
            "calculator_grid",
            path=str(_COMPONENT_DIR),
        )
    return _calculator_grid


def render_calculator_grid(payload: dict[str, Any], *, key: str = "calculator_grid") -> str | None:
    """Render the mini-spreadsheet grid and return JSON actions from the browser."""

    component = _calculator_grid_component()
    return component(payload=payload, key=key, default=None)


__all__ = ["render_calculator_grid"]
