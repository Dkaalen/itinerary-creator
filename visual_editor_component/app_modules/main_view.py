"""Compatibility shim for the removed legacy Streamlit app shell.

The active UI is ``app_modules.main_view``.
"""

from app_modules.main_view import render_app, render_final_preview_step


def render_sidebar_controls() -> bool:
    return False


def render_app_hero(app_version):
    return None


def render_workflow_overview():
    return None


def render_input_step():
    return None


def render_edit_step():
    return None


def render_add_pictures_step():
    return None
