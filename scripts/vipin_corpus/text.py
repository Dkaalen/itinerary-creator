"""Text normalization helpers for Vipin corpus runner."""

from __future__ import annotations

import re
from typing import Any


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm_key(value: Any) -> str:
    return _norm(value).lower()


def _number_like(value: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", _norm(value)))
