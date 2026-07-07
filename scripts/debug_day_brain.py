"""Emit a developer-facing Day Brain report for supplier text fixtures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generator import group_rows_by_day
from itinerary_generation.day_brain_report import build_day_brain_report
from itinerary_parser import parse_itinerary

DEFAULT_FIXTURE = ROOT / "tests/fixtures/real_inputs/finland_norway_winter_family.txt"


def report_for_file(path: Path) -> dict:
    raw_text = path.read_text(encoding="utf-8")
    rows = parse_itinerary(raw_text)
    grouped = group_rows_by_day(rows)
    report = build_day_brain_report(grouped)
    report["fixture"] = str(path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect Day Brain facts, intent and generated copy for itinerary input.")
    parser.add_argument("paths", nargs="*", help="Supplier text fixture paths. Defaults to one real fixture.")
    args = parser.parse_args(argv)
    paths = [Path(path) for path in args.paths] or [DEFAULT_FIXTURE]
    reports = [report_for_file(path if path.is_absolute() else ROOT / path) for path in paths]
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
