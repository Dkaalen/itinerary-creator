"""Real-output QA index builders."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Callable

from scripts.real_excel_fixture_bank import DEFAULT_MANIFEST, build_candidate_index
from scripts.real_output_qa.score_reports import build_score_report
from scripts.tag_real_excel_fixture_bank import build_tag_index

DEFAULT_MD = Path(__file__).resolve().parents[2] / "docs/quality/REAL_OUTPUT_QA_INDEX.md"
DEFAULT_JSON = Path(__file__).resolve().parents[2] / "docs/reports/real_output_qa_index/latest.json"


def build_qa_index(
    *,
    sample_size: int,
    seed: int,
    manifest_path: Path = DEFAULT_MANIFEST,
    score_report_builder: Callable[..., dict] = build_score_report,
) -> dict:
    """Build the compact real-output QA index."""

    score = score_report_builder(sample_size=sample_size, seed=seed, manifest_path=manifest_path)
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
    """Render a real-output QA index markdown report."""

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
    """Write QA index markdown/json files."""

    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown_index(index), encoding="utf-8")
    json_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md_path, json_path


__all__ = ["DEFAULT_JSON", "DEFAULT_MD", "build_qa_index", "markdown_index", "write_qa_index"]
