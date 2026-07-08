"""Shared model objects for architecture guard reports."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceHit:
    path: str
    marker: str


@dataclass(frozen=True)
class SizeHit:
    path: str
    lines: int
    limit: int


@dataclass(frozen=True)
class FunctionHit:
    path: str
    name: str
    lines: int
    limit: int
