"""Compatibility facade for saved-project UI actions."""

from __future__ import annotations

from app_modules.project_browser_ui import render_open_project_file_action, render_open_project_workspace_if_visible
from app_modules.project_save_ui import render_save_project_file_action

__all__ = ["render_open_project_file_action", "render_open_project_workspace_if_visible", "render_save_project_file_action"]
