"""Measure optimization baselines without contacting live services.

The command prints JSON containing parser/normalizer timings, dirty-state timing,
and the current request shape for batched project deletion. It uses generated
or repository-owned fixture data and never reads secrets.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
import sys
from time import perf_counter
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app_modules.parse_workflow import parse_and_normalize_itinerary
from app_modules.project_persistence_state import mark_cloud_project_persisted
from app_modules.project_unsaved_state import active_project_has_unsaved_changes
from app_modules.project_workspace_revision import mark_workspace_mutated
from app_modules.session_state_keys import (
    DAY_PAGE_LAYOUT_KEY,
    DETAIL_LEVEL_KEY,
    ITINERARY_NAME_KEY,
    OUTPUT_EDITS_KEY,
    PARSED_ROWS_KEY,
    PROJECT_STORAGE_LAST_SAVED_BASELINE_KEY,
    RAW_TEXT_INPUT_KEY,
)
from project_storage.config import SupabaseStorageConfig
from project_storage.repository import ProjectStorageRepository

DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "real_inputs" / "nordic_quality_sample.txt"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    parser.add_argument("--runs", type=int, default=8, help="Timing runs per parser case.")
    args = parser.parse_args()

    report = {
        "fixture": str(DEFAULT_FIXTURE.relative_to(ROOT)),
        "parser": _parser_baseline(max(3, args.runs)),
        "unsaved_state": _unsaved_state_baseline(),
        "batched_delete_request_shape": _delete_request_shape(),
    }
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    return 0


def _parser_baseline(runs: int) -> dict[str, Any]:
    source = DEFAULT_FIXTURE.read_text(encoding="utf-8")
    lines = [line for line in source.splitlines() if line.strip()]
    result: dict[str, Any] = {}
    for multiplier in (1, 4, 12):
        text = "\n".join(lines * multiplier)
        parsed_rows = parse_and_normalize_itinerary(text)
        result[f"{len(lines) * multiplier}_source_lines"] = {
            "parsed_rows": len(parsed_rows),
            **_sample(lambda: parse_and_normalize_itinerary(text), runs=runs),
        }
    return result


def _unsaved_state_baseline() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for count in (25, 250, 1000):
        rows = [
            {
                "day": f"Day {(index // 4) + 1}",
                "type": "Activity",
                "title": f"Activity {index}",
                "city": "Oslo",
                "metadata": {"sequence": index, "tags": ["a", "b", "c"]},
            }
            for index in range(count)
        ]
        edits = {
            f"Day {(index // 4) + 1}": {
                "title": f"Day title {index // 4}",
                "blocks": [{"kind": "activity", "text": f"Activity {index}"}],
            }
            for index in range(count)
        }
        baseline = {
            "metadata": {"itinerary_name": "Benchmark"},
            "current_snapshot": {
                "parsed_rows": rows,
                "output_edits": edits,
                "detail_level": "standard",
                "day_page_layout": "auto",
            },
            "source": {"source_input": "supplier"},
        }
        plain_state = {
            PROJECT_STORAGE_LAST_SAVED_BASELINE_KEY: baseline,
            PARSED_ROWS_KEY: rows,
            OUTPUT_EDITS_KEY: edits,
            RAW_TEXT_INPUT_KEY: "supplier",
            ITINERARY_NAME_KEY: "Benchmark",
            DETAIL_LEVEL_KEY: "standard",
            DAY_PAGE_LAYOUT_KEY: "auto",
        }
        revision_state = dict(plain_state)
        mark_workspace_mutated(revision_state)
        mark_cloud_project_persisted(revision_state, payload=baseline, version_id="benchmark")
        if active_project_has_unsaved_changes(plain_state):
            raise RuntimeError("Synthetic plain workspace unexpectedly appeared dirty.")
        if active_project_has_unsaved_changes(revision_state):
            raise RuntimeError("Synthetic revision workspace unexpectedly appeared dirty.")

        def rebuild_revision_signatures() -> bool:
            mark_workspace_mutated(revision_state)
            return active_project_has_unsaved_changes(revision_state)

        result[str(count)] = {
            "uncached_comparison": _sample(
                lambda: active_project_has_unsaved_changes(plain_state),
                runs=10,
            ),
            "revision_rebuild": _sample(rebuild_revision_signatures, runs=10),
            "revision_cached_rerun": _sample(
                lambda: active_project_has_unsaved_changes(revision_state),
                runs=50,
            ),
        }
    return result


def _delete_request_shape() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for count in (1, 5, 25):
        client = _CountingDeleteClient(file_count_per_project=1)
        repository = ProjectStorageRepository(
            SupabaseStorageConfig(
                url="https://example.invalid",
                secret_key="not-used",
                bucket="project-files",
            ),
            client=client,
        )
        project_ids = tuple(f"project-{index}" for index in range(1, count + 1))
        repository.permanently_delete_itineraries(project_ids)
        result[str(count)] = {
            "total_requests": len(client.calls),
            "rest_get": sum(call[0] == "rest_get" for call in client.calls),
            "storage_delete": sum(call[0] == "storage_delete" for call in client.calls),
            "rest_delete": sum(call[0] == "rest_delete" for call in client.calls),
        }
    return result


def _sample(action: Callable[[], Any], *, runs: int) -> dict[str, Any]:
    timings = []
    for _ in range(runs):
        started = perf_counter()
        action()
        timings.append(perf_counter() - started)
    return {
        "runs": runs,
        "p50_ms": round(median(timings) * 1000, 3),
        "worst_ms": round(max(timings) * 1000, 3),
    }


class _CountingDeleteClient:
    def __init__(self, *, file_count_per_project: int) -> None:
        self.file_count_per_project = file_count_per_project
        self.calls: list[tuple[str, str]] = []

    def rest_get(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        self.calls.append(("rest_get", table))
        if table == "itinerary_files":
            raw = str(params.get("itinerary_id") or "")
            if raw.startswith("eq."):
                project_ids = (raw.removeprefix("eq."),)
            else:
                payload = raw[4:-1] if raw.startswith("in.(") and raw.endswith(")") else ""
                project_ids = tuple(value for value in payload.split(",") if value)
            return [
                {
                    "id": f"file-{project_id}-{index}",
                    "itinerary_id": project_id,
                    "storage_path": f"{project_id}/file-{index}.json",
                }
                for project_id in project_ids
                for index in range(self.file_count_per_project)
            ]
        return []

    def storage_delete(self, bucket: str, storage_paths: list[str]) -> None:
        self.calls.append(("storage_delete", bucket))

    def rest_delete(self, table: str, params: dict[str, str]) -> list[dict[str, Any]]:
        self.calls.append(("rest_delete", table))
        return []


if __name__ == "__main__":
    raise SystemExit(main())
