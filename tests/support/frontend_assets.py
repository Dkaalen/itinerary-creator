"""Frontend asset loading helpers for tests."""

from __future__ import annotations

from pathlib import Path

FRONTEND_ROOT = Path("visual_editor_component/frontend")


def frontend_script_names() -> tuple[str, ...]:
    """Return JavaScript files in the editor bootstrap order."""

    index_html = (FRONTEND_ROOT / "index.html").read_text(encoding="utf-8")
    direct_scripts = [
        line.split('src="js/', 1)[1].split('"', 1)[0]
        for line in index_html.splitlines()
        if 'src="js/' in line
    ]
    bootstrap = (FRONTEND_ROOT / "js/editor_bootstrap.js").read_text(encoding="utf-8")
    bootstrapped_scripts = [
        line.split("'js/", 1)[1].split("'", 1)[0]
        for line in bootstrap.splitlines()
        if "'js/" in line and line.strip().endswith("',")
    ]

    names: list[str] = []
    for script_name in (*direct_scripts, *bootstrapped_scripts):
        if script_name not in names:
            names.append(script_name)
    return tuple(names)


def frontend_styles_source() -> str:
    """Return editor CSS with top-level imports expanded for source-contract tests."""

    main_css = (FRONTEND_ROOT / "styles/editor.css").read_text(encoding="utf-8")
    chunks = [main_css]
    for line in main_css.splitlines():
        line = line.strip()
        if not line.startswith('@import url("'):
            continue
        css_name = line.split('"', 2)[1]
        chunks.append((FRONTEND_ROOT / "styles" / css_name).read_text(encoding="utf-8"))
    return "\n".join(chunks)


def frontend_source(*, include_styles: bool = True) -> str:
    """Return the editor frontend source as the browser loads it."""

    chunks: list[str] = []
    if include_styles:
        chunks.append(frontend_styles_source())
    chunks.extend(
        (FRONTEND_ROOT / "js" / name).read_text(encoding="utf-8")
        for name in frontend_script_names()
    )
    return "\n".join(chunks)
