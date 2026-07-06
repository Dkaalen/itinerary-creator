"""Static QA-health report for the Itinerary App test suite.

This does not run pytest. It highlights grouping, marker, and brittleness risks so
cleanup work starts from evidence instead of more test-count padding.
"""

from __future__ import annotations

import ast
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TESTS_ROOT = REPO_ROOT / "tests"

from scripts.test_groups import (  # noqa: E402
    FAST_TESTS,
    GROUPS,
    RELEASE_CANDIDATE_GROUPS,
    SLOW_TESTS,
    _module_name,
    pdf_module_names,
    quality_module_names,
    slow_direct_targets,
    slow_module_names,
)

SOURCE_STRING_RE = re.compile(
    r"assert\s+[^\n]*(?:\bin\s+text\b|\bnot\s+in\s+text\b|\bin\s+source\b|\bnot\s+in\s+source\b)"
)
DIRECT_MARK_RE = re.compile(r"@pytest\.mark\.(?!parametrize\b)([A-Za-z_][A-Za-z0-9_]*)")
PATCH_NAME_RE = re.compile(r"test_(?:patch|batch|qg|dest|input|editor|review|cleanup)[:_0-9a-zA-Z-]*\.py")


def _test_modules() -> list[Path]:
    return sorted(TESTS_ROOT.glob("test_*.py"))


def _test_function_count(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )


def _source_string_assertions(path: Path) -> int:
    return len(SOURCE_STRING_RE.findall(path.read_text(encoding="utf-8")))


def _direct_markers(path: Path) -> Counter[str]:
    return Counter(DIRECT_MARK_RE.findall(path.read_text(encoding="utf-8")))


def build_report() -> str:
    modules = _test_modules()
    group_modules = {name: {_module_name(path) for path in paths} for name, paths in GROUPS.items()}
    covered_modules = set().union(*group_modules.values())
    discovered_modules = {path.name for path in modules}
    source_string_counts = {
        path.name: count for path in modules if (count := _source_string_assertions(path))
    }
    direct_markers = Counter()
    test_counts: list[tuple[int, str]] = []
    for path in modules:
        direct_markers.update(_direct_markers(path))
        test_counts.append((_test_function_count(path), path.name))

    fast_modules = {_module_name(path) for path in FAST_TESTS}
    fast_heavy_overlap = sorted(
        fast_modules & (pdf_module_names() | slow_module_names() | quality_module_names())
    )
    patch_history_names = sorted(path.name for path in modules if PATCH_NAME_RE.match(path.name))

    lines = [
        "Test-suite QA health report",
        "===========================",
        f"Discovered test modules: {len(modules)}",
        f"Discovered test functions: {sum(count for count, _name in test_counts)}",
        f"Named runner groups: {', '.join(GROUPS)}",
        f"Release candidate groups: {', '.join(RELEASE_CANDIDATE_GROUPS)}",
        f"Modules covered by at least one named group: {len(covered_modules)}",
        f"Modules covered only by full/remaining: {len(discovered_modules - covered_modules)}",
        f"Fast group modules: {len(fast_modules)}",
        f"Fast/PDF/slow/quality overlap: {len(fast_heavy_overlap)}",
        f"Slow direct isolated targets: {len(slow_direct_targets(REPO_ROOT))}",
        f"Slow modules: {len(SLOW_TESTS)}",
        f"Direct non-parametrize pytest markers: {sum(direct_markers.values())}",
        f"Source-string assertion candidate files: {len(source_string_counts)}",
        f"Patch/history-style test filenames: {len(patch_history_names)}",
        "",
    ]

    if fast_heavy_overlap:
        lines.append("Fast group still contains heavy modules:")
        lines.extend(f"  - {name}" for name in fast_heavy_overlap)
        lines.append("")

    top_source_files = sorted(source_string_counts.items(), key=lambda item: item[1], reverse=True)[:12]
    if top_source_files:
        lines.append("Top source-string assertion candidates:")
        lines.extend(f"  - {name}: {count}" for name, count in top_source_files)
        lines.append("")

    top_count_files = sorted(test_counts, reverse=True)[:12]
    lines.append("Largest test modules by function count:")
    lines.extend(f"  - {name}: {count}" for count, name in top_count_files)
    lines.append("")

    missing_from_groups = sorted(discovered_modules - covered_modules)
    if missing_from_groups:
        lines.append("Modules not in named groups and reached only by full:")
        lines.extend(f"  - {name}" for name in missing_from_groups[:30])
        if len(missing_from_groups) > 30:
            lines.append(f"  ... {len(missing_from_groups) - 30} more")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    print(build_report(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
