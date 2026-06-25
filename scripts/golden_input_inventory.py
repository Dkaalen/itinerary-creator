"""Inventory real golden inputs used for itinerary quality hardening.

This script is developer-only. It gives patch work one stable view of the
real-world fixtures that should be exercised before changing parser,
generation, preview, or PDF behavior.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.vipin_excel_corpus import load_items_jsonl  # noqa: E402

REAL_INPUTS_DIR = REPO_ROOT / "tests" / "fixtures" / "real_inputs"
QUALITY_STRESS_DIR = REPO_ROOT / "tests" / "fixtures" / "quality_stress_inputs"
STRESS_INPUTS_DIR = REPO_ROOT / "tests" / "fixtures" / "stress_inputs"
ACTIVITY_TRAINING_DIR = REPO_ROOT / "tests" / "fixtures" / "activity_training"
VIPIN_ITEMS_JSONL = REAL_INPUTS_DIR / "vipin_nordic_calculator_corpus_items.jsonl"
VIPIN_MANIFEST = REAL_INPUTS_DIR / "vipin_nordic_calculator_corpus_manifest.json"


@dataclass(frozen=True)
class GoldenInputInventory:
    real_input_files: int
    quality_stress_files: int
    stress_input_files: int
    activity_training_files: int
    vipin_item_count: int
    vipin_sheet_count: int
    vipin_file_counts: dict[str, int]
    vipin_top_type_counts: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def total_fixture_files(self) -> int:
        return (
            self.real_input_files
            + self.quality_stress_files
            + self.stress_input_files
            + self.activity_training_files
        )


def _fixture_files(root: Path, suffixes: tuple[str, ...] = (".txt", ".md", ".json", ".jsonl", ".tsv")) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def summarize_golden_inputs() -> GoldenInputInventory:
    vipin_items = load_items_jsonl(VIPIN_ITEMS_JSONL) if VIPIN_ITEMS_JSONL.exists() else []
    type_counts = Counter((item.row_type or "").lower() for item in vipin_items)
    file_counts = Counter(item.file for item in vipin_items)
    return GoldenInputInventory(
        real_input_files=len(_fixture_files(REAL_INPUTS_DIR)),
        quality_stress_files=len(_fixture_files(QUALITY_STRESS_DIR)),
        stress_input_files=len(_fixture_files(STRESS_INPUTS_DIR)),
        activity_training_files=len(_fixture_files(ACTIVITY_TRAINING_DIR)),
        vipin_item_count=len(vipin_items),
        vipin_sheet_count=len({(item.file, item.sheet) for item in vipin_items}),
        vipin_file_counts=dict(sorted(file_counts.items())),
        vipin_top_type_counts=dict(type_counts.most_common(20)),
    )


def load_vipin_manifest() -> dict[str, Any]:
    if not VIPIN_MANIFEST.exists():
        return {}
    return json.loads(VIPIN_MANIFEST.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize real golden itinerary input fixtures.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output.")
    args = parser.parse_args(argv)

    summary = summarize_golden_inputs()
    inventory = summary.as_dict()
    inventory["total_fixture_files"] = summary.total_fixture_files
    inventory["vipin_manifest"] = load_vipin_manifest()
    print(json.dumps(inventory, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
