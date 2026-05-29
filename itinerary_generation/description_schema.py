"""Data structures for composed activity descriptions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DescriptionDraft:
    text: str
    source: str
    warnings: list[str]


