"""Shared text helpers for group-tour presentation adapters."""

import re
from typing import Any, Iterable, Sequence

SPACE_RE = re.compile(r"\s+")


def clean(value: Any) -> str:
    return SPACE_RE.sub(" ", str(value or "").replace("\xa0", " ")).strip(" \t\r\n-|:")


def unique(values: Iterable[str]) -> list[str]:
    result, seen = [], set()
    for value in values:
        text = clean(value); key = text.casefold()
        if text and key not in seen: seen.add(key); result.append(text)
    return result


def natural_join(values: Sequence[str]) -> str:
    items = [str(value).strip() for value in values if str(value).strip()]
    if len(items) < 2: return items[0] if items else ""
    if len(items) == 2: return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"
