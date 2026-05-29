"""Shared time text cleanup."""

from __future__ import annotations

import re

def clean_time_text(value: str) -> str:
    text = " ".join(str(value or "").replace("\xa0", " ").split()).strip()
    # Some general text polish can turn decimal durations into "5. 5 Hrs".
    # Normalize that back before duration parsing so all layers see 5.5 hours.
    text = re.sub(r"(\d)\s*([\.,])\s*(\d)", r"\1.\3", text)
    return text


