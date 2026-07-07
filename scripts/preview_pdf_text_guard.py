"""Guard preview/PDF-facing itinerary text from the render context."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.review_real_output_text import build_reviews
from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST

BANNED_PDF_TEXT = (
    "Actvity Upgrade",
    "Free wifi",
    "Guest Hose",
    "Centraly Located",
    "Travel from Shuttle transfer",
)


def _review_text(review: Any) -> str:
    parts = [review.trip_title, review.trip_subtitle, review.route]
    for day in review.days:
        parts.extend([day.title, day.city, day.intro])
        parts.extend(day.transport)
        parts.extend(day.accommodation)
        parts.extend(day.activities)
        parts.extend(day.leisure)
        parts.extend(day.optional_experiences)
    parts.extend(review.included)
    parts.extend(review.optional_addons)
    parts.extend(review.not_included)
    return "\n".join(part for part in parts if part)


def build_text_guard_report(*, fixture_ids=(), sample_size: int = 3, seed: int = 6200, manifest_path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    reviews = build_reviews(manifest_path=manifest_path, sample_size=sample_size, seed=seed, fixture_ids=fixture_ids)
    fixtures = []
    error_count = 0
    for review in reviews:
        text = _review_text(review)
        missing_required = []
        for required in (review.trip_title, review.route):
            if required and required not in text:
                missing_required.append(required)
        banned = [phrase for phrase in BANNED_PDF_TEXT if phrase.casefold() in text.casefold()]
        errors = []
        if missing_required:
            errors.append({"code": "render_text_missing_required", "phrases": missing_required})
        if banned:
            errors.append({"code": "pdf_facing_banned_text", "phrases": banned})
        error_count += len(errors)
        fixtures.append({
            "fixture_id": review.fixture.get("fixture_id", ""),
            "day_count": len(review.days),
            "char_count": len(text),
            "errors": errors,
        })
    return {"seed": seed, "sample_size": len(reviews), "error_count": error_count, "fixtures": fixtures}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate preview/PDF-facing render text for real Excel outputs.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--sample-size", type=int, default=3)
    parser.add_argument("--seed", type=int, default=6200)
    parser.add_argument("--fixture", "--candidate", action="append", default=[])
    args = parser.parse_args(argv)
    report = build_text_guard_report(
        fixture_ids=args.fixture,
        sample_size=args.sample_size,
        seed=args.seed,
        manifest_path=Path(args.manifest),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["error_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
