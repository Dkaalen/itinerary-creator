"""Serialization helpers for real-output QA reports."""

from __future__ import annotations

import json
from typing import Sequence

from scripts.real_output_qa.models import CandidateOutputReview


def reviews_to_json(reviews: Sequence[CandidateOutputReview]) -> str:
    return json.dumps([review.to_dict() for review in reviews], ensure_ascii=False, indent=2)


__all__ = ["reviews_to_json"]
