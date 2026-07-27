"""Pure paging helpers for the compact cloud-project manager."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Iterable

from project_storage.project_results import ProjectListResult

PROJECT_PAGE_SIZE = 25


@dataclass(frozen=True)
class ProjectPage:
    """One bounded project-list page plus navigation metadata."""

    projects: tuple[dict[str, Any], ...]
    page_index: int
    page_size: int
    has_previous: bool
    has_next: bool
    total_count: int | None = None

    @property
    def number(self) -> int:
        return self.page_index + 1

    @property
    def first_item_number(self) -> int:
        if not self.projects:
            return 0
        return (self.page_index * self.page_size) + 1

    @property
    def last_item_number(self) -> int:
        if not self.projects:
            return 0
        return self.first_item_number + len(self.projects) - 1

    @property
    def total_pages(self) -> int:
        if self.total_count is None:
            return self.number + int(self.has_next)
        return max(1, ceil(max(0, self.total_count) / self.page_size))

    @property
    def last_page_index(self) -> int:
        """Return the nearest valid zero-based page after a shrinking result set."""

        return max(0, self.total_pages - 1)


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


def build_counted_project_page(
    result: ProjectListResult,
    *,
    page_index: int,
    page_size: int = PROJECT_PAGE_SIZE,
) -> ProjectPage:
    """Adapt an exact-count repository page into the Explorer paging model."""

    clean_page = max(0, int(page_index))
    clean_size = max(1, int(page_size))
    total = max(0, int(result.total_count))
    return ProjectPage(
        projects=tuple(result.projects),
        page_index=clean_page,
        page_size=clean_size,
        has_previous=clean_page > 0,
        has_next=((clean_page + 1) * clean_size) < total,
        total_count=total,
    )
