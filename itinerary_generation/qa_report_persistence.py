"""Persist QA reports to disk."""

from __future__ import annotations

import json
from pathlib import Path

from itinerary_generation.qa_report_model import QaReport, qa_reports_dir
from itinerary_generation.qa_report_rendering import render_qa_report_json, render_qa_report_markdown


def persist_qa_report(report: QaReport, base_dir: Path | None = None) -> dict[str, str]:
    base = base_dir or qa_reports_dir()
    base.mkdir(parents=True, exist_ok=True)
    safe_stamp = report.generated_at.replace(":", "").replace("+", "Z")
    stem = f"qa_report_{safe_stamp}_{report.report_id}"
    json_path = base / f"{stem}.json"
    md_path = base / f"{stem}.md"
    json_path.write_text(render_qa_report_json(report), encoding="utf-8")
    md_path.write_text(render_qa_report_markdown(report), encoding="utf-8")
    index_path = base / "index.jsonl"
    with index_path.open("a", encoding="utf-8") as index_file:
        index_file.write(json.dumps({
            "report_id": report.report_id,
            "generated_at": report.generated_at,
            "app_version": report.app_version,
            "draft_id": report.draft_id,
            "edited_items": report.summary.get("edited_items", 0),
            "warnings": report.summary.get("warnings", 0),
            "json_path": str(json_path),
            "markdown_path": str(md_path),
        }, ensure_ascii=False) + "\n")
    return {"json_path": str(json_path), "markdown_path": str(md_path), "index_path": str(index_path)}
