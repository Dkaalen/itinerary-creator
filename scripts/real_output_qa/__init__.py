"""Real-output QA package."""

from scripts.real_output_qa.models import *  # noqa: F403
from scripts.real_output_qa.rendering import render_candidate, render_candidate_review
from scripts.real_output_qa.scoring import score_rendered_output
from scripts.real_output_qa.segments import iter_output_segments, rendered_output_text
from scripts.real_output_qa.serialization import reviews_to_json

__all__ = [
    "CandidateOutputReview",
    "CandidateRenderError",
    "CandidateRenderResult",
    "DayOutputSnapshot",
    "OutputTextIssue",
    "OutputTextScore",
    "TextSegment",
    "iter_output_segments",
    "render_candidate",
    "render_candidate_review",
    "rendered_output_text",
    "reviews_to_json",
    "score_rendered_output",
]
