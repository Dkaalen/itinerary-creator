"""Shared text helpers for itinerary row normalization."""

import re

def clean_space(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()

def get_row_type(row: dict) -> str:
    return row.get("effective_type") or row.get("type", "")

def text_blob(row: dict) -> str:
    parts = [
        row.get("city", ""),
        row.get("title", ""),
        row.get("original_title", ""),
        row.get("details", ""),
        " ".join(row.get("includes", []) or []),
    ]
    return clean_space(" ".join(str(part or "") for part in parts))

def _lower_key(value: str) -> str:
    return re.sub(r"[^a-z0-9åäöøæéü -]+", " ", str(value or "").lower()).strip()

