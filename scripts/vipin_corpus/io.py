"""JSONL IO helpers for Vipin corpus items and bad-output logs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from scripts.vipin_corpus.models import BadOutput, ExcelCorpusItem


def load_items_jsonl(path: str | Path) -> list[ExcelCorpusItem]:
    """Load pre-extracted corpus rows from a JSONL fixture."""

    input_path = Path(path)
    items: list[ExcelCorpusItem] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid corpus JSONL at {input_path}:{line_number}: {exc}") from exc
            items.append(ExcelCorpusItem.from_dict(payload))
    return items


def write_items_jsonl(items: Iterable[ExcelCorpusItem], path: str | Path) -> None:
    """Write extracted corpus rows as a stable JSONL fixture."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for item in items:
            handle.write(json.dumps(item.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def write_bad_outputs_jsonl(bad_outputs: Iterable[BadOutput], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for bad_output in bad_outputs:
            handle.write(json.dumps(bad_output.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
