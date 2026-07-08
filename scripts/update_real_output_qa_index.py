"""Write a small QA index from real-output scoring runs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST
from scripts.real_output_qa.indexing import DEFAULT_JSON, DEFAULT_MD, markdown_index, write_qa_index
from scripts.real_output_qa.score_reports import build_score_report
from scripts.real_output_qa.indexing import build_qa_index as _build_qa_index


def build_qa_index(*, sample_size: int, seed: int, manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    """Build the QA index while preserving monkeypatchable score-report ownership."""

    return _build_qa_index(
        sample_size=sample_size,
        seed=seed,
        manifest_path=manifest_path,
        score_report_builder=build_score_report,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update the real-output QA index files.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--sample-size", type=int, default=5)
    parser.add_argument("--seed", type=int, default=6200)
    parser.add_argument("--md-output", default=str(DEFAULT_MD))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON))
    args = parser.parse_args(argv)
    index = build_qa_index(sample_size=args.sample_size, seed=args.seed, manifest_path=Path(args.manifest))
    md_path, json_path = write_qa_index(index, Path(args.md_output), Path(args.json_output))
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    return 1 if index["score_report"]["error_count"] else 0


__all__ = ["DEFAULT_JSON", "DEFAULT_MD", "build_qa_index", "markdown_index", "write_qa_index"]


if __name__ == "__main__":
    raise SystemExit(main())
