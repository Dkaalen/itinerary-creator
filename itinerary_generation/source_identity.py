"""Compatibility exports for neutral source-row helpers.

New code should import from :mod:`shared.source_rows`. This module remains as a
stable compatibility path for older tests and extensions.
"""

from __future__ import annotations

from shared.source_rows import (  # noqa: F401
    DISPLAY_SOURCE_TEXT_FIELDS,
    SOURCE_TEXT_FIELDS,
    clean_text,
    edit_row_id,
    row_ids_for_rows,
    rows_by_source_id,
    source_row_id,
    source_text,
)
