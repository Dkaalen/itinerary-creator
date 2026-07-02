"""Python bridge for the browser-side calculator grid component."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).resolve().parent / "frontend"

_calculator_grid = components.declare_component(
    "calculator_grid",
    path=str(_COMPONENT_DIR),
)


def render_calculator_grid(payload: dict[str, Any], *, key: str = "calculator_grid") -> str | None:
    """Render the mini-spreadsheet grid and return JSON actions from the browser."""

    return _calculator_grid(payload=payload, key=key, default=None)
