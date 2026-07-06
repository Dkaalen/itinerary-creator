from __future__ import annotations


def test_workspace_shell_does_not_disable_page_scroll() -> None:
    from ui import style_app_shell

    css = style_app_shell.CSS

    assert "overflow-y: auto !important;" in css
    assert ".block-container:has(.studio-brand-link)" in css
    assert "overflow: visible !important;" in css
    assert "overflow: hidden !important;\n    margin-top: 1.15rem" not in css
