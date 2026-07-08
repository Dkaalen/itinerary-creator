r"""Benchmark the text-cleanup contribution to the main itinerary workflow.

Run from the repository root, for example:

    python .\scripts\benchmark_text_cleanup.py --repeats 3
    python .\scripts\benchmark_text_cleanup.py --all-fixtures --include-pdf

The benchmark measures parse/normalize, generated edit state, preview HTML,
visual-editor payload, shared render context, and optionally typed PDF export.
It reports cold and warm timings separately together with cache hit statistics.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time
from typing import Any, Callable, Iterable


DEFAULT_FIXTURES = (
    "finland_winter_quality_check.txt",
    "iceland_group_tour_winter.txt",
    "iceland_self_drive_summer.txt",
    "scandinavia_cruise_premium_working.txt",
)


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _normalise_project_paths(value: str, project_root: Path) -> str:
    return str(value).replace(str(project_root), "<PROJECT_ROOT>")


def _select_fixture_paths(
    project_root: Path,
    fixture_names: Iterable[str] | None,
    *,
    all_fixtures: bool,
) -> list[Path]:
    fixture_root = project_root / "tests" / "fixtures" / "real_inputs"
    available = {path.name: path for path in fixture_root.glob("*.txt")}
    if all_fixtures:
        return [available[name] for name in sorted(available)]

    names = tuple(fixture_names or DEFAULT_FIXTURES)
    missing = [name for name in names if name not in available]
    if missing:
        raise FileNotFoundError(f"Missing benchmark fixture(s): {', '.join(missing)}")
    return [available[name] for name in names]


def _ensure_project_import_path(project_root: Path) -> None:
    project_root_text = str(project_root)
    if project_root_text not in sys.path:
        sys.path.insert(0, project_root_text)


def _workflow_functions() -> dict[str, Callable[..., Any]]:
    from app_modules.itinerary_html import build_itinerary_html
    from app_modules.itinerary_render_context import build_itinerary_render_context
    from itinerary_generation.common import group_rows_by_day
    from itinerary_parser import parse_itinerary
    from normalizer import normalize_itinerary_rows
    from pdf_exporter_modules.typed_exporter import export_render_document_to_pdf
    from ui.output_edits import make_output_edit_state
    from visual_editor_component.editor_payload_builder import build_visual_editor_payload

    return {
        "build_itinerary_html": build_itinerary_html,
        "build_itinerary_render_context": build_itinerary_render_context,
        "build_visual_editor_payload": build_visual_editor_payload,
        "export_render_document_to_pdf": export_render_document_to_pdf,
        "group_rows_by_day": group_rows_by_day,
        "make_output_edit_state": make_output_edit_state,
        "normalize_itinerary_rows": normalize_itinerary_rows,
        "parse_itinerary": parse_itinerary,
    }


def _empty_timings() -> dict[str, float]:
    return {
        "parse_normalize": 0.0,
        "edit_state": 0.0,
        "preview_html": 0.0,
        "editor_payload": 0.0,
        "render_context": 0.0,
        "typed_pdf_export": 0.0,
    }


def _empty_counts(source_count: int) -> dict[str, int]:
    return {
        "fixtures": source_count,
        "rows": 0,
        "html_bytes": 0,
        "editor_bytes": 0,
        "pdf_bytes": 0,
    }


def _benchmark_source(
    name: str,
    source: str,
    project_root: Path,
    workflow: dict[str, Callable[..., Any]],
    timings: dict[str, float],
    counts: dict[str, int],
    digest: "hashlib._Hash",
):
    started = time.perf_counter()
    rows = workflow["normalize_itinerary_rows"](workflow["parse_itinerary"](source))
    grouped = workflow["group_rows_by_day"](rows)
    timings["parse_normalize"] += time.perf_counter() - started
    counts["rows"] += len(rows)

    started = time.perf_counter()
    edits = workflow["make_output_edit_state"](rows, grouped)
    edits["draft_id"] = f"benchmark-{Path(name).stem}"
    timings["edit_state"] += time.perf_counter() - started

    started = time.perf_counter()
    html = workflow["build_itinerary_html"](rows, grouped, edits)
    timings["preview_html"] += time.perf_counter() - started
    counts["html_bytes"] += len(html.encode("utf-8"))

    started = time.perf_counter()
    editor = workflow["build_visual_editor_payload"](rows, grouped, edits)
    timings["editor_payload"] += time.perf_counter() - started
    editor_json = json.dumps(editor, sort_keys=True, ensure_ascii=False, default=str)
    counts["editor_bytes"] += len(editor_json.encode("utf-8"))

    started = time.perf_counter()
    context = workflow["build_itinerary_render_context"](rows, grouped, edits)
    timings["render_context"] += time.perf_counter() - started

    deterministic_edits = dict(edits)
    deterministic_edits.pop("draft_id", None)
    digest.update(name.encode("utf-8"))
    digest.update(json.dumps(rows, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
    digest.update(json.dumps(deterministic_edits, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
    digest.update(_normalise_project_paths(html, project_root).encode("utf-8"))
    digest.update(_normalise_project_paths(editor_json, project_root).encode("utf-8"))
    return context


def _export_pdf_contexts(
    contexts: list[tuple[str, Any]],
    workflow: dict[str, Callable[..., Any]],
    timings: dict[str, float],
    counts: dict[str, int],
) -> None:
    with tempfile.TemporaryDirectory(prefix="itinerary_text_cleanup_benchmark_") as temp_dir:
        for name, context in contexts:
            pdf_path = Path(temp_dir) / f"{Path(name).stem}.pdf"
            started = time.perf_counter()
            workflow["export_render_document_to_pdf"](
                context.render_document,
                pdf_path,
                color_data=context.colors,
            )
            timings["typed_pdf_export"] += time.perf_counter() - started
            counts["pdf_bytes"] += pdf_path.stat().st_size


def _run_once(
    sources: list[tuple[str, str]],
    project_root: Path,
    workflow: dict[str, Callable[..., Any]],
    *,
    include_pdf: bool,
) -> tuple[dict[str, float], dict[str, int], str]:
    timings = _empty_timings()
    counts = _empty_counts(len(sources))
    digest = hashlib.sha256()
    contexts = []

    for name, source in sources:
        context = _benchmark_source(name, source, project_root, workflow, timings, counts, digest)
        contexts.append((name, context))

    if include_pdf:
        _export_pdf_contexts(contexts, workflow, timings, counts)

    return timings, counts, digest.hexdigest()


def _warm_medians(warm_runs: list[dict[str, float]], stages: Iterable[str]) -> dict[str, float]:
    return {stage: _median([run[stage] for run in warm_runs]) for stage in stages}


def run_benchmark(
    project_root: Path,
    *,
    fixture_names: Iterable[str] | None = None,
    all_fixtures: bool = False,
    repeats: int = 3,
    include_pdf: bool = False,
) -> dict:
    """Run the representative workflow benchmark and return JSON-safe metrics."""

    project_root = Path(project_root).resolve()
    _ensure_project_import_path(project_root)

    from shared.text_cleanup_cache import clear_text_cleanup_caches, text_cleanup_cache_snapshot

    workflow = _workflow_functions()
    fixture_paths = _select_fixture_paths(project_root, fixture_names, all_fixtures=all_fixtures)
    sources = [(path.name, path.read_text(encoding="utf-8")) for path in fixture_paths]

    clear_text_cleanup_caches()
    gc.collect()
    cold_timings, counts, cold_digest = _run_once(sources, project_root, workflow, include_pdf=include_pdf)
    cold_cache = text_cleanup_cache_snapshot()

    warm_runs = []
    warm_digests = []
    for _ in range(max(1, int(repeats))):
        gc.collect()
        timings, _counts, digest = _run_once(sources, project_root, workflow, include_pdf=include_pdf)
        warm_runs.append(timings)
        warm_digests.append(digest)

    warm_medians = _warm_medians(warm_runs, cold_timings)
    return {
        "fixtures": [path.name for path in fixture_paths],
        "counts": counts,
        "cold_seconds": cold_timings,
        "warm_median_seconds": warm_medians,
        "cold_total_seconds": sum(cold_timings.values()),
        "warm_total_median_seconds": sum(warm_medians.values()),
        "output_digest": cold_digest,
        "warm_output_identical": all(digest == cold_digest for digest in warm_digests),
        "cache_after_cold": cold_cache,
        "cache_after_warm": text_cleanup_cache_snapshot(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--fixture", action="append", default=[])
    parser.add_argument("--all-fixtures", action="store_true")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--include-pdf", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    result = run_benchmark(
        args.project_root,
        fixture_names=args.fixture or None,
        all_fixtures=args.all_fixtures,
        repeats=args.repeats,
        include_pdf=args.include_pdf,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
