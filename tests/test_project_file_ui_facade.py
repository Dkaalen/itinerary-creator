from __future__ import annotations

from pathlib import Path
from tests.support.static_contracts import read_contract_text

import app_modules.project_file_ui as project_file_ui
from app_modules.project_browser_ui import render_open_project_file_action
from app_modules.project_save_ui import render_save_project_file_action


def test_project_file_ui_is_thin_compatibility_facade() -> None:
    source = read_contract_text("app_modules/project_file_ui.py")

    assert project_file_ui.render_open_project_file_action is render_open_project_file_action
    assert project_file_ui.render_save_project_file_action is render_save_project_file_action
    assert "import streamlit" not in source
    assert len(source.splitlines()) <= 12
