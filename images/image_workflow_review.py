"""Image workflow review summaries for picture-stage state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ImageWorkflowReview:
    required_days: int
    matched_days: int
    unmatched_days: tuple[str, ...]
    warning_count: int
    error_count: int
    status_label: str
    low_quality_days: tuple[str, ...] = ()
    replacement_option_count: int = 0

    @property
    def coverage_text(self) -> str:
        return f"{self.matched_days}/{self.required_days} days matched" if self.required_days else "No day images required"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["unmatched_days"] = list(self.unmatched_days)
        data["low_quality_days"] = list(self.low_quality_days)
        data["coverage_text"] = self.coverage_text
        return data


def _match_needs_quality_review(match: Mapping[str, Any] | None) -> bool:
    if not isinstance(match, Mapping):
        return False
    if match.get("is_default"):
        return True
    try:
        if int(match.get("score") or 0) and int(match.get("score") or 0) < 45:
            return True
    except (TypeError, ValueError):
        pass
    audit = match.get("audit") if isinstance(match.get("audit"), Mapping) else {}
    return bool(audit.get("stronger_candidate_available") or match.get("stronger_candidate_available"))


def build_image_workflow_review(
    grouped_days: Mapping[str, Any] | None,
    image_matches: Mapping[str, Any] | None,
    warnings: Iterable[Any] | None = None,
    replacement_options_by_day: Mapping[str, Iterable[Any]] | None = None,
) -> ImageWorkflowReview:
    grouped_days = grouped_days or {}
    image_matches = image_matches or {}
    warnings = tuple(warnings or ())

    required = [str(day) for day in grouped_days]
    matched = [
        day for day in required
        if isinstance(image_matches.get(day), Mapping)
        and (image_matches[day].get("path") or image_matches[day].get("data_uri"))
    ]
    unmatched = tuple(day for day in required if day not in matched)
    low_quality = tuple(
        day for day in required
        if day in matched and _match_needs_quality_review(image_matches.get(day))
    )
    replacement_options_by_day = replacement_options_by_day or {}
    replacement_option_count = sum(len(tuple(options or ())) for options in replacement_options_by_day.values())
    error_count = sum(1 for warning in warnings if getattr(warning, "severity", "") == "error")
    warning_count = len(warnings)

    if error_count or unmatched:
        status = "Needs review"
    elif warning_count or low_quality:
        status = "Review"
    else:
        status = "Clear"
    return ImageWorkflowReview(
        required_days=len(required),
        matched_days=len(matched),
        unmatched_days=unmatched,
        warning_count=warning_count,
        error_count=error_count,
        status_label=status,
        low_quality_days=low_quality,
        replacement_option_count=replacement_option_count,
    )
