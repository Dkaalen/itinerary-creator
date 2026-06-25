"""Client-output quality gate for generated itinerary render documents."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from itinerary_generation.client_sanitizer import contains_price_or_currency
from itinerary_generation.client_text_decisions import is_weak_journey_arc_phrase
from itinerary_generation.generation_quality_gate import BLOCKING, WARNING, ItineraryValidationIssue
from itinerary_generation.quality_gate_patterns import (
    AURORA_REVIEW_PATTERN,
    FORBIDDEN_CLIENT_PATTERNS,
    PRICE_CLIENT_PATTERN_MESSAGE,
    RAW_SUPPLIER_FIELD_RE,
    SUPPLIER_TIME_WARNING_RE,
    SUSPICIOUS_AM_PM_TIME_RANGE_RE,
)

@dataclass(frozen=True)
class ClientOutputQualityGateReport:
    """Validation report for generated client-facing render output."""

    issues: tuple[ItineraryValidationIssue, ...] = field(default_factory=tuple)

    @property
    def blocking_issues(self) -> tuple[ItineraryValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == BLOCKING)

    @property
    def warnings(self) -> tuple[ItineraryValidationIssue, ...]:
        return tuple(issue for issue in self.issues if issue.severity == WARNING)

    @property
    def is_blocked(self) -> bool:
        return bool(self.blocking_issues)


def _append_text(parts: list[str], value: Any) -> None:
    if value is None:
        return
    if isinstance(value, str):
        if value.strip():
            parts.append(value)
        return
    if isinstance(value, Mapping):
        for item in value.values():
            _append_text(parts, item)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _append_text(parts, item)
        return
    # Dataclasses/typed render objects expose useful public attributes.
    for name in getattr(value, "__dataclass_fields__", {}) or {}:
        _append_text(parts, getattr(value, name, None))


def render_document_text(render_document: Any) -> str:
    """Flatten generated render output for late client-quality validation."""

    parts: list[str] = []
    _append_text(parts, render_document)
    return "\n".join(parts)




def raw_supplier_scan_text(render_document: Any) -> str:
    """Flatten only client prose that should never contain raw supplier headings.

    Legitimate app-owned final-section titles such as "What’s included" are not
    leaks; supplier headings are leaks when they survive inside day blocks, meta
    values, descriptions, bullets, or custom paragraph content.
    """

    parts: list[str] = []
    for day in getattr(render_document, "days", []) or []:
        _append_text(parts, getattr(day, "title", ""))
        _append_text(parts, getattr(day, "intro", ""))
        for block in getattr(day, "blocks", []) or []:
            _append_text(parts, getattr(block, "title", ""))
            _append_text(parts, getattr(block, "meta", []))
            _append_text(parts, getattr(block, "includes", []))
            _append_text(parts, getattr(block, "description", ""))
            _append_text(parts, getattr(block, "notable_sights", []))
            _append_text(parts, getattr(block, "lines", []))
            _append_text(parts, getattr(block, "extra_sections", []))
    for section in getattr(render_document, "final_sections", []) or []:
        for page in getattr(section, "pages", []) or []:
            _append_text(parts, getattr(page, "items", []))
            _append_text(parts, getattr(page, "paragraphs", []))
            _append_text(parts, getattr(page, "content_html", ""))
            for page_section in getattr(page, "sections", []) or []:
                _append_text(parts, getattr(page_section, "items", []))
    return "\n".join(parts)


def _meta_lines_with_time_warnings(render_document: Any) -> list[str]:
    findings: list[str] = []
    for day in getattr(render_document, "days", []) or []:
        for block in getattr(day, "blocks", []) or []:
            for meta in getattr(block, "meta", []) or []:
                label = str(getattr(meta, "label", "") or "")
                value = str(getattr(meta, "value", "") or "")
                if "time" in label.lower() and SUPPLIER_TIME_WARNING_RE.search(value):
                    findings.append(f"{getattr(day, 'day', '')} / {getattr(block, 'title', '')}: {value}")
    return findings



def _journey_arc_phrase_issues(render_document: Any) -> list[ItineraryValidationIssue]:
    """Find meaning-level Journey Arc filler, not just exact forbidden words."""

    issues: list[ItineraryValidationIssue] = []
    summary = getattr(render_document, "summary", None)
    rows = getattr(summary, "journey_arc", []) or []
    for row in rows:
        if isinstance(row, Mapping):
            chapter = str(row.get("chapter", "") or "")
            experience = row.get("experience", "")
        else:
            chapter = str(getattr(row, "chapter", "") or "")
            experience = getattr(row, "experience", "")
        if is_weak_journey_arc_phrase(experience):
            issues.append(
                ItineraryValidationIssue(
                    BLOCKING,
                    "weak_journey_arc_meaning",
                    "Journey Arc contains generic logistics filler instead of a destination, route, or real experience.",
                    context=f"{chapter}: {experience}",
                )
            )
    return issues

def _bare_activity_blocks(render_document: Any) -> list[str]:
    findings: list[str] = []
    for day in getattr(render_document, "days", []) or []:
        for block in getattr(day, "blocks", []) or []:
            if str(getattr(block, "kind", "") or "") != "activity":
                continue
            title = str(getattr(block, "title", "") or "").strip()
            has_supporting_text = bool(
                getattr(block, "includes", None)
                or str(getattr(block, "description", "") or "").strip()
                or getattr(block, "notable_sights", None)
                or getattr(block, "extra_sections", None)
            )
            if title and not has_supporting_text:
                findings.append(f"{getattr(day, 'day', '')}: {title}")
    return findings


def _image_payload_is_default(match: Mapping[str, Any]) -> bool:
    if bool(match.get("is_default") or match.get("is_generic")):
        return True
    city = str(match.get("city", "") or "").strip().lower()
    filename = str(match.get("filename", "") or "").strip().lower()
    path = str(match.get("path", "") or "").replace("\\", "/").lower()
    return city in {"default", "defoult"} or "/default/" in path or filename.startswith("default_")


def _image_match_issues(day_images: Mapping[str, Mapping[str, Any] | None] | None) -> list[ItineraryValidationIssue]:
    # Default/fallback pictures are no longer a final-output blocker.  The app
    # may still record image metadata for diagnostics, but PDF creation should
    # not be stopped by a picture-review state.
    return []


def _image_bank_status_issues(image_bank_status: Mapping[str, Any] | None) -> list[ItineraryValidationIssue]:
    if not isinstance(image_bank_status, Mapping):
        return []
    missing = bool(
        image_bank_status.get("missing_full_bank")
        or image_bank_status.get("default_only")
        or image_bank_status.get("is_default_only")
        or not image_bank_status.get("full_bank_found", image_bank_status.get("using_full_destination_bank", False))
    )
    if not missing:
        return []
    message = str(
        image_bank_status.get("blocking_message")
        or "Full destination image bank is missing; default-only picture selection cannot be approved."
    )
    return [
        ItineraryValidationIssue(
            BLOCKING,
            "image_bank_full_missing",
            message,
            context=str(image_bank_status.get("source_path") or image_bank_status.get("paths") or ""),
        )
    ]


def evaluate_client_output_quality(
    render_document: Any,
    *,
    day_images: Mapping[str, Mapping[str, Any] | None] | None = None,
    image_bank_status: Mapping[str, Any] | None = None,
) -> ClientOutputQualityGateReport:
    """Validate final generated client output after parsing/normalization."""

    issues: list[ItineraryValidationIssue] = []
    text = render_document_text(render_document)

    for code, pattern, message in FORBIDDEN_CLIENT_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            issues.append(ItineraryValidationIssue(BLOCKING, code, message))

    if AURORA_REVIEW_PATTERN.search(text):
        issues.append(
            ItineraryValidationIssue(
                WARNING,
                "aurora_wording_review",
                "Client-facing output contains 'Aurora'. Verify it is preserved supplier/product wording; otherwise prefer 'Northern Lights'.",
            )
        )

    if SUSPICIOUS_AM_PM_TIME_RANGE_RE.search(text):
        issues.append(
            ItineraryValidationIssue(
                WARNING,
                "suspicious_am_pm_time_range",
                "Client-facing output contains a suspicious AM-to-PM time range. Review the source timing before sending to the client.",
            )
        )

    if contains_price_or_currency(text):
        issues.append(ItineraryValidationIssue(BLOCKING, "client_price_or_currency_leak", PRICE_CLIENT_PATTERN_MESSAGE))

    if RAW_SUPPLIER_FIELD_RE.search(raw_supplier_scan_text(render_document)):
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "raw_supplier_field_leak",
                "Raw supplier section labels leaked into generated client output.",
            )
        )

    for context in _meta_lines_with_time_warnings(render_document):
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "supplier_warning_in_time_field",
                "Supplier warning text leaked into a Time field.",
                context=context,
            )
        )

    for context in _bare_activity_blocks(render_document):
        issues.append(
            ItineraryValidationIssue(
                BLOCKING,
                "bare_activity_inclusion_heading",
                "Activity block has a heading but no supporting client-facing text.",
                context=context,
            )
        )

    issues.extend(_journey_arc_phrase_issues(render_document))
    issues.extend(_image_match_issues(day_images))
    issues.extend(_image_bank_status_issues(image_bank_status))
    return ClientOutputQualityGateReport(issues=tuple(issues))


def blocking_client_output_messages(render_document: Any, **kwargs: Any) -> list[str]:
    return [issue.message for issue in evaluate_client_output_quality(render_document, **kwargs).blocking_issues]

__all__ = [
    "ClientOutputQualityGateReport",
    "_append_text",
    "render_document_text",
    "raw_supplier_scan_text",
    "_meta_lines_with_time_warnings",
    "_journey_arc_phrase_issues",
    "_bare_activity_blocks",
    "_image_payload_is_default",
    "_image_match_issues",
    "_image_bank_status_issues",
    "evaluate_client_output_quality",
    "blocking_client_output_messages",
]
