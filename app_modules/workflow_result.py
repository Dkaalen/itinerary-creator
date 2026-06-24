from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WorkflowActionResult:
    """Small result object returned by workflow actions."""

    ok: bool
    stage: str
    message: str = ""
    payload: dict[str, Any] | None = None
