"""Compatibility shim for the removed legacy Streamlit app shell.

The active UI is ``app_modules.main_view``. This module intentionally no
longer contains sidebar controls, old numbered expanders, or a second app
workflow. Keeping it tiny prevents future patches from editing the wrong UI.
"""

from app_modules.main_view import render_app, render_final_preview_step


def render_sidebar_controls() -> bool:
    """Legacy hook: the rebuilt app has no sidebar workflow."""

    return False


def render_app_hero(app_version):
    """Legacy hook retained for old imports; active rendering is centralized."""

    return None


def render_workflow_overview():
    """Legacy hook retained for old imports; active rendering is centralized."""

    return None


def render_input_step():
    """Legacy hook retained for old imports; active rendering is centralized."""

    return None


def render_edit_step():
    """Legacy hook retained for old imports; active rendering is centralized."""

    return None


def render_add_pictures_step():
    """Legacy hook retained for old imports; active rendering is centralized."""

    return None
