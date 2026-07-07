"""Derive useful QA tags for real Excel fixture candidates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST, ExcelFixtureCandidate, build_candidate_index

TAG_PATTERNS: tuple[tuple[str, str], ...] = (
    ("overnight_train", r"overnight train|night train|sleeper train"),
    ("train", r"\btrain\b|railway|rail station"),
    ("ferry", r"\bferry\b|\bcruise\b|fjord cruise"),
    ("flight", r"\bflight\b|airport"),
    ("transfer_heavy", r"transfer|shuttle|coach|bus station"),
    ("hotel_change", r"\bhotel\b|accommodation"),
    ("optional_experience", r"activity upgrade|optional|upgrade"),
    ("group_tour", r"group tour|\bGTS\b|\bGTW\b"),
    ("multi_activity_day", r"activity"),
    ("full_leisure_day", r"spend time at leisure|day at leisure|free day"),
    ("northern_lights", r"northern lights|aurora"),
    ("sami", r"sámi|sami"),
    ("lapland", r"lapland|rovaniemi|levi|saariselkä|inari"),
    ("norway_in_a_nutshell", r"norway in a nutshell|flåm|flam|myrdal|voss|gudvangen"),
    ("winter", r"snow|winter|ice|arctic"),
    ("self_drive", r"self drive|rental car|car rental"),
)
COUNTRY_PATTERNS: tuple[tuple[str, str], ...] = (
    ("norway", r"norway|oslo|bergen|tromsø|tromso|flåm|flam|lofoten"),
    ("finland", r"finland|helsinki|rovaniemi|oulu|kuusamo|levi|inari|saariselkä"),
    ("iceland", r"iceland|reykjavík|reykjavik|keflavík|keflavik|akureyri"),
    ("denmark", r"denmark|copenhagen|aarhus"),
    ("sweden", r"sweden|stockholm|kiruna|abisko"),
)


def derive_candidate_tags(candidate: ExcelFixtureCandidate) -> tuple[str, ...]:
    text = f"{candidate.fixture_id}\n{candidate.raw_text}".casefold()
    tags = [str(tag).casefold().replace(" ", "_") for tag in candidate.tags]
    for tag, pattern in (*COUNTRY_PATTERNS, *TAG_PATTERNS):
        if re.search(pattern, text, flags=re.IGNORECASE):
            tags.append(tag)
    activity_days: dict[str, int] = {}
    transfer_count = 0
    countries = {tag for tag, _ in COUNTRY_PATTERNS if tag in tags}
    for line in candidate.raw_text.splitlines():
        cols = line.split("\t")
        day = cols[0].strip() if cols else ""
        row_type = cols[1].casefold() if len(cols) > 1 else ""
        if "activity" in row_type:
            activity_days[day] = activity_days.get(day, 0) + 1
        if any(word in line.casefold() for word in ("transfer", "coach", "flight", "train", "ferry")):
            transfer_count += 1
    if any(count >= 2 for count in activity_days.values()):
        tags.append("multi_activity_day")
    if transfer_count >= max(3, candidate.day_count // 2):
        tags.append("transfer_heavy")
    if len(countries) >= 2:
        tags.append("multi_country_route")
    if candidate.row_count <= 5:
        tags.append("sparse_input")
    return tuple(dict.fromkeys(tags))


def build_tag_index(candidates: Sequence[ExcelFixtureCandidate]) -> dict:
    records = []
    tag_counts: dict[str, int] = {}
    for candidate in candidates:
        tags = derive_candidate_tags(candidate)
        for tag in tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        records.append({**candidate.summary(), "tags": list(tags)})
    return {"candidate_count": len(records), "tag_counts": dict(sorted(tag_counts.items())), "candidates": records}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive QA tags for the real Excel fixture bank.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    args = parser.parse_args(argv)
    report = build_tag_index(build_candidate_index(Path(args.manifest)))
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
