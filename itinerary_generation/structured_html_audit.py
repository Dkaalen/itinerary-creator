"""Audit source-aware structured HTML after visual editing.

The structured model can link inclusions/exclusions back to source rows, but the
visual editor works with HTML fragments during the migration.  These helpers
carry source-row identity through the HTML using ``data-source-row-ids`` and
warn when an edited final page drops a required source-backed item.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from itinerary_generation.structured_model import ModelWarning, StructuredListSection
from itinerary_generation.structured_rendering import normalize_structured_list_sections


def expected_source_row_ids_for_sections(sections) -> tuple[str, ...]:
    """Return ordered unique source ids represented by structured sections."""

    seen: set[str] = set()
    ordered: list[str] = []
    for section in normalize_structured_list_sections(sections):
        for item in section.items:
            for row_id in item.source_row_ids:
                clean = str(row_id or "").strip()
                if clean and clean not in seen:
                    seen.add(clean)
                    ordered.append(clean)
    return tuple(ordered)


def source_row_ids_in_html(html: str) -> tuple[str, ...]:
    """Extract source-row ids preserved in rendered/edited HTML fragments."""

    soup = BeautifulSoup(str(html or ""), "html.parser")
    seen: set[str] = set()
    ordered: list[str] = []
    for element in soup.find_all(attrs={"data-source-row-ids": True}):
        value = element.get("data-source-row-ids") or ""
        for raw_id in str(value).split(","):
            clean = raw_id.strip()
            if clean and clean not in seen:
                seen.add(clean)
                ordered.append(clean)
    return tuple(ordered)


def validate_source_aware_html_coverage(
    *,
    html_fragments,
    sections,
    page_name: str,
    warning_code: str,
) -> tuple[ModelWarning, ...]:
    """Warn when edited final-page HTML loses source ids from structured data.

    The check is intentionally skipped when there are no expected source ids;
    many default final-page bullets are general commercial notes with no source
    row.  It also skips empty HTML because other validation already detects
    missing/broken final pages.
    """

    expected_ids = expected_source_row_ids_for_sections(sections)
    if not expected_ids:
        return ()

    if isinstance(html_fragments, (list, tuple)):
        html = "\n".join(
            str(fragment.get("html", "") if isinstance(fragment, dict) else fragment or "")
            for fragment in html_fragments
        )
    else:
        html = str(html_fragments or "")
    if not html.strip():
        return ()

    present_ids = set(source_row_ids_in_html(html))
    missing = tuple(row_id for row_id in expected_ids if row_id not in present_ids)
    if not missing:
        return ()

    return (
        ModelWarning(
            code=warning_code,
            message=(
                f"Edited {page_name} HTML is missing source-row identity for one or more "
                "structured items. Review the final page before PDF export."
            ),
            severity="warning",
            source_row_ids=missing[:20],
        ),
    )
