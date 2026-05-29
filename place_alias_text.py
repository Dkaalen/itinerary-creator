"""Text-key helpers for Nordic place aliases."""

from __future__ import annotations

import re
import unicodedata


def _strip_accents(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", str(value or ""))
        if not unicodedata.combining(ch)
    )


def _key(value: str) -> str:
    text = _strip_accents(value).lower()
    text = text.replace("æ", "ae").replace("ø", "o").replace("å", "a")
    text = text.replace("ð", "d").replace("þ", "th")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())
