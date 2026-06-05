"""Client-output layout contract checks.

The structured-model rebuild should make the internals safer without quietly
changing the client-facing document shape.  These helpers validate the stable
preview/PDF HTML contract at the boundary: page order, required final pages and
list structure.  They are intentionally conservative and presentation-aware,
while the core structured model stays presentation-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from bs4 import BeautifulSoup

ContractSeverity = Literal["warning", "error"]


@dataclass(frozen=True)
class OutputContractIssue:
    code: str
    message: str
    severity: ContractSeverity = "error"


@dataclass(frozen=True)
class OutputLayoutSignature:
    page_types: tuple[str, ...]
    final_page_titles: tuple[str, ...]
    day_count: int
    included_page_count: int
    not_included_page_count: int

    @property
    def page_count(self) -> int:
        return len(self.page_types)


def _classes(node) -> set[str]:
    return {str(value) for value in (node.get("class") or [])}


def _page_type(page) -> str:
    classes = _classes(page)
    if "cover-page" in classes:
        return "cover"
    if "summary-page" in classes:
        return "summary"
    if "day-page" in classes:
        return "day"
    if "optional-addons-page" in classes:
        return "optional_addons"
    if "important-notes-page" in classes:
        return "important_notes"
    if "categorized-inclusions-page" in classes:
        title = _page_title(page).lower()
        if "not included" in title:
            return "whats_not_included"
        return "whats_included"
    if "categorized-exclusions-page" in classes:
        return "whats_not_included"
    if "final-list-page" in classes:
        title = _page_title(page).lower()
        if "what" in title and "included" in title and "not" not in title:
            return "whats_included"
        if "not included" in title:
            return "whats_not_included"
        return "final_list"
    return "unknown"


def _page_title(page) -> str:
    title = page.select_one(".final-page-title")
    return " ".join(title.get_text(" ").split()) if title else ""


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(str(html or ""), "html.parser")


def extract_output_layout_signature(html: str) -> OutputLayoutSignature:
    """Return the client-facing page shape of rendered itinerary HTML."""

    soup = _soup(html)
    pages = soup.select(".a4-page")
    page_types = tuple(_page_type(page) for page in pages)
    final_titles = tuple(_page_title(page) for page in pages if _page_title(page))
    return OutputLayoutSignature(
        page_types=page_types,
        final_page_titles=final_titles,
        day_count=page_types.count("day"),
        included_page_count=page_types.count("whats_included"),
        not_included_page_count=page_types.count("whats_not_included"),
    )


def _first_index(values: Iterable[str], target: str) -> int | None:
    for index, value in enumerate(values):
        if value == target:
            return index
    return None


def _has_list_structure(page) -> bool:
    return bool(page.select("li, .inclusion-category-block, .content-block"))


def _looks_like_collapsed_exclusions(page) -> bool:
    """Detect the broken one-paragraph 'What's not included' failure mode."""

    if page.select("li, .inclusion-category-block"):
        return False
    text = " ".join(page.get_text(" ").split()).lower()
    markers = [
        "international flights",
        "self-arranged flights",
        "travel insurance",
        "meals unless",
        "personal expenses",
        "optional extras",
    ]
    return sum(1 for marker in markers if marker in text) >= 3


def validate_output_layout_contract(html: str, expected_day_count: int | None = None) -> tuple[OutputContractIssue, ...]:
    """Validate the stable A4 output shape before allowing client PDF export."""

    soup = _soup(html)
    pages = soup.select(".a4-page")
    page_types = tuple(_page_type(page) for page in pages)
    issues: list[OutputContractIssue] = []

    if not pages:
        return (OutputContractIssue("no_a4_pages", "Rendered output contains no A4 pages."),)

    if page_types[0] != "cover":
        issues.append(OutputContractIssue("cover_page_not_first", "The cover page is missing or is not the first page."))
    if len(page_types) < 2 or page_types[1] != "summary":
        issues.append(OutputContractIssue("summary_page_not_second", "The summary page is missing or is not the second page."))

    day_count = page_types.count("day")
    if expected_day_count is not None and day_count != expected_day_count:
        issues.append(OutputContractIssue(
            "day_page_count_mismatch",
            f"Rendered day-page count is {day_count}, expected {expected_day_count}.",
        ))
    elif day_count == 0:
        issues.append(OutputContractIssue("no_day_pages", "Rendered output contains no itinerary day pages."))

    included_index = _first_index(page_types, "whats_included")
    not_included_index = _first_index(page_types, "whats_not_included")
    notes_index = _first_index(page_types, "important_notes")
    first_day_index = _first_index(page_types, "day")

    if included_index is None:
        issues.append(OutputContractIssue("missing_whats_included", "The What’s included page is missing."))
    if not_included_index is None:
        issues.append(OutputContractIssue("missing_whats_not_included", "The What’s not included page is missing."))
    if notes_index is None:
        issues.append(OutputContractIssue("missing_important_notes", "The Important travel notes page is missing."))

    if first_day_index is not None and included_index is not None and included_index < first_day_index:
        issues.append(OutputContractIssue("included_before_days", "The What’s included page appears before itinerary day pages."))
    if included_index is not None and not_included_index is not None and not_included_index < included_index:
        issues.append(OutputContractIssue("exclusions_before_inclusions", "The What’s not included page appears before What’s included."))
    if not_included_index is not None and notes_index is not None and notes_index < not_included_index:
        issues.append(OutputContractIssue("notes_before_exclusions", "Important travel notes appear before What’s not included."))

    for page in pages:
        page_type = _page_type(page)
        if page_type not in {"whats_included", "whats_not_included"}:
            continue
        if not _has_list_structure(page):
            issues.append(OutputContractIssue(
                f"{page_type}_has_no_list_structure",
                f"The {_page_title(page) or page_type} page has no list/category structure.",
            ))
        if page_type == "whats_not_included" and _looks_like_collapsed_exclusions(page):
            issues.append(OutputContractIssue(
                "collapsed_whats_not_included",
                "The What’s not included page appears to have collapsed into one paragraph.",
            ))

    return tuple(dict.fromkeys(issues))


__all__ = [
    "OutputContractIssue",
    "OutputLayoutSignature",
    "extract_output_layout_signature",
    "validate_output_layout_contract",
]
