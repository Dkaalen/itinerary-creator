import re

from itinerary_generation.clipboard_sanitizer import strip_clipboard_fragment_markers


def clean_visual_editor_html(value):
    """Sanitize editable-page HTML before it is reused in preview/PDF.

    The visual editor is an internal editing surface, but we still strip risky
    tags/attributes and normalize accidental browser artifacts so custom day
    blocks remain safe and close to the PDF display model.
    """
    text = strip_clipboard_fragment_markers(value)
    if not text.strip():
        return ""
    text = re.sub(
        r"<\s*(script|style|iframe|object|embed)[^>]*>.*?<\s*/\s*\1\s*>",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r'''\s+on[a-zA-Z]+\s*=\s*(["\']).*?\1''', "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\s+on[a-zA-Z]+\s*=\s*[^\s>]+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"javascript\s*:", "", text, flags=re.IGNORECASE)
    text = re.sub(r'''contenteditable=(["\']).*?\1''', "", text, flags=re.IGNORECASE)
    text = re.sub(r'''data-edit-key=(["\']).*?\1''', "", text, flags=re.IGNORECASE)
    text = re.sub(r'''\s+style=(["\']).*?\1''', "", text, flags=re.IGNORECASE | re.DOTALL)
    return text.strip()


_FINAL_LIST_BOUNDARY_PHRASES = (
    "International flights unless specifically listed",
    "Self-arranged flights",
    "Flight from",
    "Self-arranged flights or transport unless specifically stated as included",
    "Tickets or services marked as excluded or to be bought on site",
    "Meals unless specifically stated",
    "Drinks unless specifically stated",
    "Porterage unless specified",
    "Self transfers and self-arranged travel costs unless specifically stated",
    "Travel insurance",
    "Optional extras and personal expenses",
    "Optional experiences unless specifically confirmed",
    "Optional add-ons and experiences unless specifically selected",
    "City taxes or local fees, where applicable",
)


def _split_collapsed_final_list_text(text):
    """Split common final-page list text after browser/contenteditable damage."""

    text = " ".join(str(text or "").replace("\xa0", " ").split()).strip()
    if not text:
        return []

    marked = text
    # Put a line boundary before known commercial/default exclusion phrases. This
    # rescues the common contenteditable failure mode where a UL becomes one long
    # text run with no bullets or punctuation.
    for phrase in sorted(_FINAL_LIST_BOUNDARY_PHRASES, key=len, reverse=True):
        marked = re.sub(rf"\s+({re.escape(phrase)})", r"\n\1", marked, flags=re.IGNORECASE)

    lines = []
    for chunk in marked.replace(";", "\n").split("\n"):
        clean = " ".join(chunk.split()).strip(" •-*|")
        if clean:
            lines.append(clean)
    return lines or ([text] if text else [])


def normalize_final_list_html(value):
    """Return safe list HTML for final pages that must remain bullet/list based.

    This is intentionally narrower than ``clean_visual_editor_html``. It is used
    for pages such as "What's not included" where paragraph fallback has caused
    broken client output. Existing list HTML is preserved; collapsed text is
    converted back to a bullet list.
    """

    html = clean_visual_editor_html(value)
    if not html:
        return ""
    if re.search(r"<\s*li\b", html, flags=re.IGNORECASE):
        return html

    text = re.sub(r"<\s*br\s*/?\s*>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</\s*(?:div|p|h[1-6])\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    items = _split_collapsed_final_list_text(text)
    if not items:
        return ""
    escaped = "".join(f"<li>{_escape_html(item)}</li>" for item in items)
    return f'<ul class="final-list">{escaped}</ul>'


def _escape_html(value):
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
