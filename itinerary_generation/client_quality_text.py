"""Extract client-visible text from typed render documents."""

from typing import Any, Mapping


def append_text(parts: list[str], value: Any) -> None:
    if value is None: return
    if isinstance(value, str):
        if value.strip(): parts.append(value)
        return
    if isinstance(value, Mapping):
        for item in value.values(): append_text(parts, item)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value: append_text(parts, item)
        return
    for name in getattr(value, "__dataclass_fields__", {}) or {}: append_text(parts, getattr(value, name, None))


def render_document_text(render_document: Any) -> str:
    parts = []; append_text(parts, render_document); return "\n".join(parts)


def raw_supplier_scan_text(render_document: Any) -> str:
    parts = []
    for day in getattr(render_document, "days", []) or []:
        for value in (getattr(day, "title", ""), getattr(day, "intro", "")): append_text(parts, value)
        for block in getattr(day, "blocks", []) or []:
            for name in ("title", "meta", "includes", "description", "notable_sights", "lines", "extra_sections"): append_text(parts, getattr(block, name, []))
    for section in getattr(render_document, "final_sections", []) or []:
        for page in getattr(section, "pages", []) or []:
            for name in ("items", "paragraphs", "content_html"): append_text(parts, getattr(page, name, []))
            for child in getattr(page, "sections", []) or []: append_text(parts, getattr(child, "items", []))
    return "\n".join(parts)
