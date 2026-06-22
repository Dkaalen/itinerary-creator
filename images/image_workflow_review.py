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

    @property
    def coverage_text(self) -> str:
        return f"{self.matched_days}/{self.required_days} days matched" if self.required_days else "No day images required"

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["unmatched_days"] = list(self.unmatched_days)
        data["coverage_text"] = self.coverage_text
        return data


def build_image_workflow_review(
    grouped_days: Mapping[str, Any] | None,
    image_matches: Mapping[str, Any] | None,
    warnings: Iterable[Any] | None = None,
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
    error_count = sum(1 for warning in warnings if getattr(warning, "severity", "") == "error")
    warning_count = len(warnings)

    if error_count or unmatched:
        status = "Needs review"
    elif warning_count:
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
    )
