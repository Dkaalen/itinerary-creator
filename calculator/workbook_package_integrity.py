"""XLSX package-integrity cleanup for regenerated formulas."""
from __future__ import annotations

import re

_CALC_CHAIN_REL_RE = re.compile(
    r'<Relationship\b(?=[^>]*\bType="[^"]*/calcChain")(?=[^>]*\bTarget="[^"]*calcChain\.xml")[^>]*/>',
    re.IGNORECASE,
)
_CALC_CHAIN_OVERRIDE_RE = re.compile(
    r'<Override\b(?=[^>]*\bPartName="/xl/calcChain\.xml")(?=[^>]*\bContentType="[^"]*calcChain[^"]*")[^>]*/>',
    re.IGNORECASE,
)


def remove_calc_chain_relationship(xml: str) -> str:
    """Remove the workbook relationship to a stale calculation chain."""

    return _CALC_CHAIN_REL_RE.sub("", xml)


def remove_calc_chain_content_type(xml: str) -> str:
    """Remove the content-type registration for a deleted calculation chain."""

    return _CALC_CHAIN_OVERRIDE_RE.sub("", xml)


__all__ = ["remove_calc_chain_content_type", "remove_calc_chain_relationship"]
