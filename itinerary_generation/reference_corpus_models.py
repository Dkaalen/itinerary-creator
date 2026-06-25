"""Immutable records exposed by the versioned reference corpus."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StandardInputTemplate:
    record_id: str
    service_type: str
    source_destination: str
    canonical_destination: str
    template_text: str
    placeholders: tuple[str, ...]


@dataclass(frozen=True)
class CleanActivityReference:
    record_id: str
    record_type: str
    source_city: str
    canonical_city: str
    activity_location: str
    canonical_activity_location: str
    activity_text: str
    conditional_markers: tuple[str, ...]


@dataclass(frozen=True)
class ReferenceCorpusIssue:
    code: str
    severity: str
    corpus: str
    record_id: str
    message: str


@dataclass(frozen=True)
class ReferenceCorpusSummary:
    version: str
    standard_template_count: int
    clean_activity_count: int
    iceland_sheet_count: int
    iceland_row_count: int
    issue_count: int
    blocking_issue_count: int
