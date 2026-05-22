import re


def clean_visual_editor_html(value):
    """Sanitize editable-page HTML before it is reused in preview/PDF.

    The visual editor is an internal editing surface, but we still strip risky
    tags/attributes and normalize accidental browser artifacts so custom day
    blocks remain safe and close to the PDF display model.
    """
    text = str(value or "")
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
