"""Text-key helpers for Nordic place aliases."""

from __future__ import annotations

import re
import unicodedata


def _strip_accents(value: str) -> str:
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", str(value or ""))
        if not unicodedata.combining(ch)
    )


def normalize_place_key(value: object) -> str:
    """Return the accent-insensitive Nordic lookup key used by all place registries."""

    text = _strip_accents(str(value or "")).lower()
    text = text.replace("æ", "ae").replace("ø", "o").replace("å", "a")
    text = text.replace("ð", "d").replace("þ", "th")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _key(value: object) -> str:
    """Compatibility alias for the former private place-key helper."""

    return normalize_place_key(value)


__all__ = ["_key", "_strip_accents", "normalize_place_key"]
