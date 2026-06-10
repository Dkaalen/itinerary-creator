"""Small dependency-free text helpers shared across parsing and rendering layers."""

from __future__ import annotations

from typing import Any


def clean_space(value: Any) -> str:
    """Normalize whitespace without changing the supplier meaning."""

    return (
        " ".join(
            str(value or "")
            .replace("\xa0", " ")
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .split()
        )
        .strip()
    )


# Backward-friendly alias for older source-identity naming.
clean_text = clean_space
