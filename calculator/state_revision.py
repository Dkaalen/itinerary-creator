"""Stable revision identity for canonical Calculator state."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from calculator.calculator_state import CalculatorState


def calculator_state_revision(state: CalculatorState) -> str:
    """Return a stable editable-state revision for browser draft protection.

    Currency-rate and presentation changes do not invalidate an unsynced browser
    draft. Only canonical Calculator rows and passenger count define ownership.
    """

    payload = {
        "rows": [asdict(row) for row in state.rows],
        "number_of_pax": state.number_of_pax,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


__all__ = ["calculator_state_revision"]
