from __future__ import annotations

from pathlib import Path


def test_workspace_shell_does_not_disable_page_scroll() -> None:
    css = Path("ui/style_app_shell.py").read_text(encoding="utf-8")

    assert "overflow-y: auto !important;" in css
    assert ".block-container:has(.studio-brand-link)" in css
    assert "overflow: visible !important;" in css
    assert "overflow: hidden !important;\n    margin-top: 1.15rem" not in css
