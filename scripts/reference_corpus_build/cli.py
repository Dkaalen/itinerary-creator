"""Command-line orchestration for rebuilding the reference corpus."""

import argparse
from pathlib import Path
from scripts.reference_corpus_build.common import CORPUS_VERSION
from scripts.reference_corpus_build.manifest import build_manifest
from scripts.reference_corpus_build.tabular import build_clean_activities, build_standard_templates
from scripts.reference_corpus_build.xlsx import build_iceland_reference


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--standard-inputs", required=True, type=Path); parser.add_argument("--activities", required=True, type=Path); parser.add_argument("--iceland-workbook", required=True, type=Path); parser.add_argument("--output-dir", type=Path, default=Path("itinerary_generation/data/reference_corpus") / CORPUS_VERSION); args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    standard = build_standard_templates(args.standard_inputs, args.output_dir / "standard_input_templates.tsv"); activities = build_clean_activities(args.activities, args.output_dir / "clean_activity_inputs.tsv"); sheets, rows = build_iceland_reference(args.iceland_workbook, args.output_dir / "iceland_standard_itinerary.json")
    build_manifest(args.output_dir, standard_source=args.standard_inputs, activity_source=args.activities, iceland_source=args.iceland_workbook, standard_count=standard, activity_count=activities, iceland_sheet_count=sheets, iceland_row_count=rows)
    print(f"Built {CORPUS_VERSION}: {standard} standard templates, {activities} activities, {sheets} Iceland sheets / {rows} rows")
    return 0
