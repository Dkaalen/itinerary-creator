"""Shared cleanup for browser clipboard marker residue.

Browsers and rich-text editors can include ``StartFragment``/``EndFragment``
markers when content is pasted or copied through HTML clipboards. Those markers
are implementation details and must never reach client-facing preview/PDF text.
"""

from __future__ import annotations

import re
from html import unescape

_FRAGMENT_MARKER_RE = re.compile(
    r"(?:<!--\s*)?(?:StartFragment|EndFragment)(?:\s*-->)?",
    flags=re.IGNORECASE,
)
_FRAGMENT_BOUNDARY_RE = re.compile(r"\s{2,}")


def strip_clipboard_fragment_markers(value: object) -> str:
    """Remove browser clipboard fragment markers from text or HTML strings."""

    text = str(value or "")
    if not text:
        return ""
    text = unescape(text)
    text = _FRAGMENT_MARKER_RE.sub("", text)
    # When markers appear inline (for example ``StartFragmentBergen``), do not
    # force whitespace into the surrounding word. When they were comments or
    # separated by whitespace, normalize the accidental gaps they leave behind.
    return _FRAGMENT_BOUNDARY_RE.sub(" ", text).strip()
