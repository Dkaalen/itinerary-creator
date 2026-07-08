"""Real-output QA package."""

from scripts.real_output_qa.indexing import build_qa_index, markdown_index, write_qa_index
from scripts.real_output_qa.markdown import build_markdown_report, write_reports
from scripts.real_output_qa.models import *  # noqa: F403
from scripts.real_output_qa.random_checks import build_random_quality_report, review_candidate
from scripts.real_output_qa.rendering import render_candidate, render_candidate_review
from scripts.real_output_qa.score_reports import build_score_report
from scripts.real_output_qa.scoring import score_rendered_output
from scripts.real_output_qa.segments import iter_output_segments, rendered_output_text
from scripts.real_output_qa.selection import build_reviews, select_candidates
from scripts.real_output_qa.serialization import reviews_to_json

__all__ = [
    "CandidateOutputReview",
    "CandidateRenderError",
    "CandidateRenderResult",
    "DayOutputSnapshot",
    "OutputTextIssue",
    "OutputTextScore",
    "TextSegment",
    "build_markdown_report",
    "build_qa_index",
    "build_random_quality_report",
    "build_reviews",
    "build_score_report",
    "iter_output_segments",
    "markdown_index",
    "render_candidate",
    "render_candidate_review",
    "rendered_output_text",
    "review_candidate",
    "reviews_to_json",
    "score_rendered_output",
    "select_candidates",
    "write_qa_index",
    "write_reports",
]
