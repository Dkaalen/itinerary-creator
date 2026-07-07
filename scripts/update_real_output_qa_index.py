"""Write a small QA index from real-output scoring runs."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.score_real_output_text import build_score_report
from scripts.tag_real_excel_fixture_bank import build_tag_index
from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST, build_candidate_index

DEFAULT_MD = ROOT / "docs/quality/REAL_OUTPUT_QA_INDEX.md"
DEFAULT_JSON = ROOT / "docs/reports/real_output_qa_index/latest.json"


def build_qa_index(*, sample_size: int, seed: int, manifest_path: Path = DEFAULT_MANIFEST) -> dict:
    score = build_score_report(sample_size=sample_size, seed=seed, manifest_path=manifest_path)
    issue_counts = Counter()
    failing = []
    for review in score["reviews"]:
        codes = [issue["code"] for issue in review["score"]["issues"]]
        issue_counts.update(codes)
        if codes:
            failing.append({"fixture_id": review["fixture"]["fixture_id"], "codes": codes, "score": review["score"]["score"]})
    tag_index = build_tag_index(build_candidate_index(manifest_path))
    return {"score_report": score, "issue_counts": dict(issue_counts), "fixtures_with_issues": failing, "tag_counts": tag_index["tag_counts"]}


def markdown_index(index: dict) -> str:
    score = index["score_report"]
    lines = [
        "# Real Output QA Index",
        "",
        f"Latest seed: `{score['seed']}`",
        f"Reviewed fixtures: `{score['sample_size']}`",
        f"Errors: `{score['error_count']}` · Warnings: `{score['warning_count']}` · Average score: `{score['average_score']}`",
        "",
        "## Selected fixtures",
    ]
    for fixture_id in score["selected_fixture_ids"]:
        lines.append(f"- `{fixture_id}`")
    lines.extend(["", "## Issue counts"])
    if index["issue_counts"]:
        for code, count in sorted(index["issue_counts"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- `{code}`: {count}")
    else:
        lines.append("- None detected")
    lines.extend(["", "## Fixtures needing review"])
    if index["fixtures_with_issues"]:
        for item in index["fixtures_with_issues"]:
            lines.append(f"- `{item['fixture_id']}` · score `{item['score']}` · {', '.join(item['codes'])}")
    else:
        lines.append("- None detected")
    lines.extend(["", "## Fixture tag coverage"])
    for tag, count in sorted(index["tag_counts"].items(), key=lambda item: (-item[1], item[0]))[:30]:
        lines.append(f"- `{tag}`: {count}")
    return "\n".join(lines).rstrip() + "\n"


def write_qa_index(index: dict, md_path: Path = DEFAULT_MD, json_path: Path = DEFAULT_JSON) -> tuple[Path, Path]:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown_index(index), encoding="utf-8")
    json_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md_path, json_path


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


if __name__ == "__main__":
    raise SystemExit(main())
