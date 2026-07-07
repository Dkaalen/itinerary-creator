"""Static QA-health report for the Itinerary App test suite.

This does not run pytest. It highlights grouping, marker, legacy-name, and
brittleness risks so cleanup work starts from evidence instead of test-count
padding.  The source-contract detector is intentionally conservative: behavior
tests that assert generated customer text are not treated as fake source-string
coverage just because they use a variable called ``text``.
"""

from __future__ import annotations

import ast
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TESTS_ROOT = REPO_ROOT / "tests"

from scripts.test_groups import (  # noqa: E402
    CRITICAL_TESTS,
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

DIRECT_MARK_RE = re.compile(r"@pytest\.mark\.(?!parametrize\b)([A-Za-z_][A-Za-z0-9_]*)")
PATCH_NAME_RE = re.compile(r"test_(?:patch_|batch[0-9a-z]*_|qg_|(?:dest|input|editor|review|cleanup)\d)[0-9a-zA-Z_-]*\.py")
SOURCE_FILE_HINTS = (
    "app_modules/",
    "calculator/",
    "calculator_grid_component/",
    "itinerary_generation/",
    "images/",
    "parser_modules/",
    "pdf_exporter_modules/",
    "project_storage/",
    "ui/",
    "visual_editor_component/",
    "scripts/",
    ".github/",
)


def _test_modules() -> list[Path]:
    return sorted(TESTS_ROOT.glob("test_*.py"))


def _test_function_count(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )


def _direct_markers(path: Path) -> Counter[str]:
    return Counter(DIRECT_MARK_RE.findall(path.read_text(encoding="utf-8")))


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(part.value for part in node.values if isinstance(part, ast.Constant) and isinstance(part.value, str))
    return None


def _looks_like_source_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    if any(hint in normalized for hint in SOURCE_FILE_HINTS):
        return True
    return normalized.endswith((".py", ".js", ".css", ".yml", ".yaml", ".html")) and not normalized.startswith("tests/fixtures/")


def _read_text_source_vars(tree: ast.AST) -> set[str]:
    vars_: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue
        func = call.func
        if not isinstance(func, ast.Attribute) or func.attr != "read_text":
            continue
        source_hint = ast.unparse(func.value) if hasattr(ast, "unparse") else ""
        literal_args = [value for arg in ast.walk(func.value) if (value := _literal_string(arg))]
        if not any(_looks_like_source_path(value) for value in literal_args) and "ROOT" not in source_hint and "Path" not in source_hint:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                vars_.add(target.id)
    return vars_


def _source_contract_assertions(path: Path) -> int:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    source_vars = _read_text_source_vars(tree)
    if not source_vars:
        return 0
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        if not any(isinstance(op, (ast.In, ast.NotIn)) for op in test.ops):
            continue
        names = {name.id for name in ast.walk(test) if isinstance(name, ast.Name)}
        if names & source_vars:
            count += 1
    return count


def _read_text_behavior_assertions(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    # Lightweight signal only: this often means useful generated-output checks,
    # not fake implementation locking.
    return len(re.findall(r"assert\s+[^\n]*(?:\bin\s+text\b|\bnot\s+in\s+text\b)", text))


def _explicit_static_contract_helper_used(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return "tests.support.static_contracts" in text or "read_contract_text(" in text


def _format_list(items: Iterable[str], *, limit: int = 30) -> list[str]:
    values = list(items)
    lines = [f"  - {item}" for item in values[:limit]]
    if len(values) > limit:
        lines.append(f"  ... {len(values) - limit} more")
    return lines


def build_report() -> str:
    modules = _test_modules()
    group_modules = {name: {_module_name(path) for path in paths} for name, paths in GROUPS.items()}
    covered_modules = set().union(*group_modules.values())
    discovered_modules = {path.name for path in modules}
    source_contract_counts = {
        path.name: count for path in modules if (count := _source_contract_assertions(path))
    }
    behavior_text_counts = {
        path.name: count for path in modules if (count := _read_text_behavior_assertions(path))
    }
    explicit_static_contracts = sorted(
        path.name for path in modules if _explicit_static_contract_helper_used(path)
    )
    direct_markers = Counter()
    test_counts: list[tuple[int, str]] = []
    for path in modules:
        direct_markers.update(_direct_markers(path))
        test_counts.append((_test_function_count(path), path.name))

    critical_modules = {_module_name(path) for path in CRITICAL_TESTS}
    fast_modules = {_module_name(path) for path in FAST_TESTS}
    heavy_modules = pdf_module_names() | slow_module_names() | quality_module_names()
    critical_heavy_overlap = sorted(critical_modules & heavy_modules)
    fast_heavy_overlap = sorted(fast_modules & heavy_modules)
    critical_source_contracts = sorted(critical_modules & set(source_contract_counts))
    fast_source_contracts = sorted(fast_modules & set(source_contract_counts))
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
        f"Critical group modules: {len(critical_modules)}",
        f"Fast group modules: {len(fast_modules)}",
        f"Critical/PDF/slow/quality overlap: {len(critical_heavy_overlap)}",
        f"Fast/PDF/slow/quality overlap: {len(fast_heavy_overlap)}",
        f"Critical source-contract assertion files: {len(critical_source_contracts)}",
        f"Fast source-contract assertion files: {len(fast_source_contracts)}",
        f"Slow direct isolated targets: {len(slow_direct_targets(REPO_ROOT))}",
        f"Slow modules: {len(SLOW_TESTS)}",
        f"Direct non-parametrize pytest markers: {sum(direct_markers.values())}",
        f"Source-file contract assertion files: {len(source_contract_counts)}",
        f"Explicit static-contract helper files: {len(explicit_static_contracts)}",
        f"Generated-output text assertion files: {len(behavior_text_counts)}",
        f"Patch/history-style test filenames: {len(patch_history_names)}",
        "",
    ]

    if critical_heavy_overlap:
        lines.append("Critical group still contains heavy modules:")
        lines.extend(_format_list(critical_heavy_overlap))
        lines.append("")
    if fast_heavy_overlap:
        lines.append("Fast group still contains heavy modules:")
        lines.extend(_format_list(fast_heavy_overlap))
        lines.append("")
    if critical_source_contracts or fast_source_contracts:
        lines.append("Instant lanes still contain implementation source-contract tests:")
        lines.extend(_format_list([*critical_source_contracts, *fast_source_contracts]))
        lines.append("")

    top_source_files = sorted(source_contract_counts.items(), key=lambda item: item[1], reverse=True)[:12]
    if top_source_files:
        lines.append("Top source-file contract assertion candidates:")
        lines.extend(f"  - {name}: {count}" for name, count in top_source_files)
        lines.append("")

    if explicit_static_contracts:
        lines.append("Explicit static-contract helper files:")
        lines.extend(_format_list(explicit_static_contracts, limit=12))
        lines.append("")

    top_count_files = sorted(test_counts, reverse=True)[:12]
    lines.append("Largest test modules by function count:")
    lines.extend(f"  - {name}: {count}" for count, name in top_count_files)
    lines.append("")

    missing_from_groups = sorted(discovered_modules - covered_modules)
    if missing_from_groups:
        lines.append("Modules not in named groups and reached only by full:")
        lines.extend(_format_list(missing_from_groups))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    print(build_report(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
