"""Client-facing text cleanup rule facade.

The canonical rule tables live in ``shared.text_cleanup_rules`` so parser,
polish and real-output QA checks use one source of truth.  This module keeps
legacy imports stable for tests and older call sites.
"""

from __future__ import annotations

from shared.text_cleanup_rules import (  # noqa: F401
    CASE_REPLACEMENTS,
    COMPILED_CASE_REPLACEMENTS,
    PROPER_NOUN_REPLACEMENTS,
    apply_case_replacements,
)

__all__ = [
    "CASE_REPLACEMENTS",
    "PROPER_NOUN_REPLACEMENTS",
    "COMPILED_CASE_REPLACEMENTS",
    "apply_case_replacements",
]
