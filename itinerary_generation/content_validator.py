"""Quality validation for canonical/generated itinerary content.

This module is deliberately pessimistic.  It is used by tests and tooling to
catch raw supplier/admin fragments before a patch is considered shippable.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    ("mechanical_day_intro", r"\bThe arrangements in\b"),
    ("opening_hours_in_title", r"Opening Hours\s*:"),
    ("misspelled_includes", r"\bIncludese\b"),
    ("bad_ticket_case", r"(?-i:\bTIckets\b)"),
    ("misspelled_excursion", r"(?-i:\bExcurssion\b)"),
    ("raw_tickets_included", r"Tickets Included\s*:"),
    ("bad_fractional_duration_spacing", r"\b2\.\s+5\s*hr\b"),
    ("raw_leisure_title", r"\bLeisure as requested\b"),
    ("raw_accommodation_prefix", r"Accommodation\s*:\s*Check[- ]?in at"),
    ("duplicate_departure_home", r"\bDeparture home\b"),
    ("cost_not_included_leak", r"\bCost not included\b"),
    ("self_arranged_raw_case", r"\bSelf Arranged\b"),
    ("old_breakfast_wording", r"\bWith breakfast\b"),
    ("supplier_operation_carried_out", r"\bCarried out\s*:"),
    ("supplier_operation_participanter", r"\bParticipanter\b"),
    ("broken_train_fragment", r"s compartment Overnight Train"),
    ("car_drive_destination", r"\bCAR\s*·\s*DRIVE\b"),
    ("standalone_local_bullet", r"<li>\s*Local\s*</li>"),
    ("fløibanen_bad_duration", r"Fløibanen[\s\S]{0,500}Duration:</span>\s*5[–-]8 minutes"),
    ("internal_icebreaker_note", r"There are 2 options in Icebreaker"),
]


@dataclass(slots=True)
class QualityFinding:
    code: str
    message: str
    context: str = ""


@dataclass(slots=True)
class FixtureQualityReport:
    fixture_name: str
    day_count: int
    row_count: int
    findings: list[QualityFinding] = field(default_factory=list)
    day_summaries: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.findings


def compact_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = text.replace("&amp;", "&").replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def validate_html(html: str) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    plain = compact_html(html)
    for code, pattern in FORBIDDEN_PATTERNS:
        target = html if "<" in pattern else plain
        if re.search(pattern, target, flags=re.IGNORECASE):
            match = re.search(pattern, target, flags=re.IGNORECASE)
            start = max(0, (match.start() if match else 0) - 80)
            end = min(len(target), (match.end() if match else 0) + 120)
            findings.append(QualityFinding(code, f"Forbidden pattern matched: {code}", target[start:end]))
    return findings


def extract_day_summaries(html: str) -> list[str]:
    summaries: list[str] = []
    for match in re.finditer(r'<section class="day-section" data-day="([^"]+)">([\s\S]*?)</section>', html):
        day = match.group(1)
        body = match.group(2)
        title_match = re.search(r'<div class="day-title">([\s\S]*?)</div>', body)
        desc_match = re.search(r'<div class="section-title small-section">Description</div>\s*<div class="body-text muted-note">([\s\S]*?)</div>', body)
        title = compact_html(title_match.group(1) if title_match else "")
        desc = compact_html(desc_match.group(1) if desc_match else "")
        summaries.append(f"{day}: title={title!r}; description_preview={desc[:140]!r}")
    return summaries
