"""Compatibility facade for real-output QA helpers.

The implementation is split under ``scripts.real_output_qa`` so reporting,
segment extraction and scoring can evolve independently.  Existing CLI scripts
and tests may keep importing this module.
"""

from scripts.real_output_qa import (  # noqa: F401
    CandidateOutputReview,
    CandidateRenderError,
    CandidateRenderResult,
    DayOutputSnapshot,
    OutputTextIssue,
    OutputTextScore,
    TextSegment,
    iter_output_segments,
    render_candidate,
    render_candidate_review,
    rendered_output_text,
    reviews_to_json,
    score_rendered_output,
)
from scripts.real_output_qa.rules import (  # noqa: F401
    ACTIVITY_TRANSPORT_EXPERIENCE_RE,
    ACTIVITY_TYPE_RE,
    AIRPORT_STAY_RE,
    CURRENCY_CODES,
    GENERIC_COPY_RE,
    RAW_SUPPLIER_FRAGMENT_RE,
    ROUTE_FALSE_PLACE_RE,
    SUPPLIER_TYPO_PATTERNS,
    SUSPICIOUS_PHRASES,
    TRANSFER_AS_PLACE_RE,
    TRANSPORT_PRODUCT_RE,
)
from scripts.real_output_qa.segments import _optional_addon_line  # noqa: F401
from scripts.real_output_qa.text_utils import _add_issue, _clean_text, _clip  # noqa: F401

__all__ = [
    "ACTIVITY_TRANSPORT_EXPERIENCE_RE",
    "ACTIVITY_TYPE_RE",
    "AIRPORT_STAY_RE",
    "CURRENCY_CODES",
    "GENERIC_COPY_RE",
    "RAW_SUPPLIER_FRAGMENT_RE",
    "ROUTE_FALSE_PLACE_RE",
    "SUPPLIER_TYPO_PATTERNS",
    "SUSPICIOUS_PHRASES",
    "TRANSFER_AS_PLACE_RE",
    "TRANSPORT_PRODUCT_RE",
    "CandidateOutputReview",
    "CandidateRenderError",
    "CandidateRenderResult",
    "DayOutputSnapshot",
    "OutputTextIssue",
    "OutputTextScore",
    "TextSegment",
    "_add_issue",
    "_clean_text",
    "_clip",
    "_optional_addon_line",
    "iter_output_segments",
    "render_candidate",
    "render_candidate_review",
    "rendered_output_text",
    "reviews_to_json",
    "score_rendered_output",
]
