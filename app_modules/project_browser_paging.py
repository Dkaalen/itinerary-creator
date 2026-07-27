"""Pure paging helpers for the compact cloud-project manager."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

PROJECT_PAGE_SIZE = 25


@dataclass(frozen=True)
class ProjectPage:
    """One bounded project-list page plus navigation metadata."""

    projects: tuple[dict[str, Any], ...]
    page_index: int
    page_size: int
    has_previous: bool
    has_next: bool

    @property
    def number(self) -> int:
        return self.page_index + 1


def build_project_page(
    rows: Iterable[dict[str, Any]],
    *,
    page_index: int,
    page_size: int = PROJECT_PAGE_SIZE,
) -> ProjectPage:
    """Trim a page-size-plus-one repository result into a stable UI page."""

    clean_page = max(0, int(page_index))
    clean_size = max(1, int(page_size))
    items = tuple(rows)
    return ProjectPage(
        projects=items[:clean_size],
        page_index=clean_page,
        page_size=clean_size,
        has_previous=clean_page > 0,
        has_next=len(items) > clean_size,
    )
