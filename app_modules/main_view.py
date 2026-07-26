from __future__ import annotations

import streamlit as st

from app_modules.calculator_navigation import calculator_page_is_active, local_library_page_is_active
from app_modules.workflow_navigation import session_stage_from_state
from layout_policy import DEFAULT_DAY_PAGE_LAYOUT


def _session_stage(state) -> str:
    return session_stage_from_state(state)


def render_calculator_page(app_version: str) -> None:
    from app_modules.calculator_page import render_calculator_page as renderer

    renderer(app_version)


def render_local_library_page(app_version: str) -> None:
    from app_modules.local_library_page import render_local_library_page as renderer

    renderer(app_version)


def render_input_page(app_version: str) -> None:
    from app_modules.input_step import render_input_page as renderer

    renderer(app_version)


def render_edit_page(app_version: str) -> None:
    from app_modules.preview_step import render_edit_page as renderer

    renderer(app_version)


def render_picture_page(app_version: str) -> None:
    from app_modules.picture_step import render_picture_page as renderer

    renderer(app_version)


def render_export_page(app_version: str) -> None:
    from app_modules.export_page import render_export_page as renderer

    renderer(app_version)


def render_debug_tools() -> None:
    from app_modules.debug_tools import render_debug_tools as renderer

    renderer()


def render_app(app_version: str, *, state=None) -> None:
    """Route first, then import and render only the active app surface.

    Production callers use Streamlit session state. Tests and other adapters may
    provide a session-like mapping so routing does not depend on mutable global
    state left behind by another workflow.
    """

    session = st.session_state if state is None else state
    session.setdefault("day_page_layout", DEFAULT_DAY_PAGE_LAYOUT)
    if calculator_page_is_active(session):
        render_calculator_page(app_version)
        render_debug_tools()
        return
    if local_library_page_is_active(session):
        render_local_library_page(app_version)
        render_debug_tools()
        return
    stage = _session_stage(session)
    if stage == "input":
        render_input_page(app_version)
    elif stage == "edit":
        render_edit_page(app_version)
    elif stage == "pictures":
        render_picture_page(app_version)
    elif stage == "export":
        render_export_page(app_version)
    else:
        render_input_page(app_version)

    render_debug_tools()
