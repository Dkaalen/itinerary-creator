from __future__ import annotations

import re
from pathlib import Path


CSS_IMPORT_RE = re.compile(r"@import\s+url\([\"']?(?P<path>[^\"')]+)[\"']?\)\s*;")


def read_frontend_text(relative: str) -> str:
    return Path("visual_editor_component/frontend", relative).read_text(encoding="utf-8")


def read_resolved_frontend_css(relative: str = "styles/editor.css", *, _seen: set[Path] | None = None) -> str:
    """Read a frontend CSS file with local @import files in browser order."""

    frontend = Path("visual_editor_component/frontend")
    path = (frontend / relative).resolve()
    seen = _seen if _seen is not None else set()
    if path in seen:
        return ""
    seen.add(path)
    text = path.read_text(encoding="utf-8")
    chunks: list[str] = []
    position = 0
    for match in CSS_IMPORT_RE.finditer(text):
        chunks.append(text[position:match.start()])
        imported = (path.parent / match.group("path")).relative_to(frontend.resolve())
        chunks.append(read_resolved_frontend_css(str(imported), _seen=seen))
        position = match.end()
    chunks.append(text[position:])
    return "\n".join(chunk for chunk in chunks if chunk)
