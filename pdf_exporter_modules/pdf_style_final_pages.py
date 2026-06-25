"""Compatibility hook for final-page style extensions."""

from __future__ import annotations


def make_final_page_styles(base):
    """Return final-page-only styles.

    Current final pages reuse shared body, section, editor, and bullet styles;
    keeping this module makes future final-page typography changes local.
    """

    return {}
