"""PDF-side HTML text extraction helpers."""

from .html_utils import clean_text


def text_with_line_breaks(tag) -> str:
    if not tag:
        return ""
    parts = []
    for node in tag.descendants:
        name = getattr(node, "name", None)
        if name == "br":
            parts.append("\n")
        elif name is None:
            parts.append(str(node))
    text = "".join(parts).replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def li_text_with_line_breaks(li) -> str:
    """Return list-item text while preserving explicit line structure."""
    direct_lines = []
    for child in li.find_all(recursive=False):
        line = clean_text(child.get_text(" "))
        if line:
            direct_lines.append(line)
    if direct_lines:
        return "\n".join(direct_lines)

    text = text_with_line_breaks(li)
    return text or clean_text(li.get_text(" "))
