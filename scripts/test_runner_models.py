"""Small data models for the staged pytest runner."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StageRunResult:
    """One pytest stage result for readable timeout diagnostics."""

    label: str
    return_code: int
    elapsed_seconds: float

    @property
    def passed(self) -> bool:
        return self.return_code == 0

    @property
    def timed_out(self) -> bool:
        return self.return_code == 124
