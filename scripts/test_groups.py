"""Central test-suite groups used by the PowerShell test runners.

The project has grown enough that a raw ``pytest -q`` run can be hard to
interpret in short-lived environments.  Keeping the suite buckets here gives
patch work a stable, readable gate while preserving a true full-suite runner.
"""

from __future__ import annotations

from pathlib import Path

from scripts.test_group_catalog import (
    ACTIVITY_TESTS,
    ARCHITECTURE_TESTS,
    BOUNDED_MODULE_TEST_SPLITS,
    CHUNKED_GROUP_STAGE_SIZES,
    CALCULATOR_BROWSER_WORKFLOW_TESTS,
    FORMULA_WORKFLOW_TESTS,
    VALIDATION_WORKFLOW_TESTS,
    WORKBOOK_WORKFLOW_TESTS,
    REALISTIC_CALCULATOR_WORKFLOW_TESTS,
    PROJECT_MANAGEMENT_WORKFLOW_TESTS,
    ROLLBACK_WORKFLOW_TESTS,
    CLOUD_LIFECYCLE_WORKFLOW_TESTS,
    RECONSTRUCTION_WORKFLOW_TESTS,
    GENERATION_WORKFLOW_TESTS,
    EDITOR_PICTURES_WORKFLOW_TESTS,
    CI_MATRIX_GROUPS,
    CRITICAL_TESTS,
    DAY_BRAIN_TESTS,
    EDITOR_TESTS,
    EMPTY_LEGACY_TEST_MODULES,
    FAST_TESTS,
    GROUP_DESCRIPTIONS,
    GROUP_ORDER,
    GROUPS,
    HEALTH_CHECK_GROUPS,
    IMAGE_TESTS,
    PARSER_TESTS,
    PDF_STAGE_SIZE,
    PDF_TESTS,
    QUALITY_TESTS,
    RELEASE_CANDIDATE_GROUPS,
    REMAINING_STAGE_SIZE,
    SLOW_TESTS,
    SLOW_TEST_SPLITS,
    STORAGE_TESTS,
    TEST_ROOT,
    TIERED_STAGE_SIZE,
    UI_TESTS,
    WORKFLOW_TESTS,
)


def _module_name(path: str) -> str:
    module_path = str(path).partition("::")[0]
    return Path(module_path).name


def existing_test_modules(repo_root: Path) -> tuple[str, ...]:
    """Return first-party pytest modules that currently contain active tests."""

    tests_dir = repo_root / TEST_ROOT
    return tuple(
        path.name
        for path in sorted(tests_dir.glob("test_*.py"))
        if path.name not in EMPTY_LEGACY_TEST_MODULES
    )


def empty_legacy_test_modules() -> frozenset[str]:
    """Return placeholder modules that are intentionally skipped by grouped runs."""

    return EMPTY_LEGACY_TEST_MODULES


def missing_group_paths(repo_root: Path) -> tuple[str, ...]:
    """Return configured group paths that no longer exist.

    Group entries may be either modules or explicit pytest node ids. Only the
    file portion should be checked on disk.
    """

    configured = sorted({path for paths in GROUPS.values() for path in paths})
    return tuple(path for path in configured if not (repo_root / path.partition("::")[0]).exists())



def chunked_group_stages(
    stage_prefix: str,
    paths: tuple[str, ...],
    stage_size: int = TIERED_STAGE_SIZE,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Split larger named lanes into readable, timeout-friendly stages."""

    if not paths:
        return ()

    chunks = tuple(
        paths[index : index + stage_size]
        for index in range(0, len(paths), stage_size)
    )
    if len(chunks) == 1:
        return ((stage_prefix, chunks[0]),)
    return tuple(
        (f"{stage_prefix} {index}/{len(chunks)}", chunk)
        for index, chunk in enumerate(chunks, start=1)
    )

def bounded_group_stages(
    stage_prefix: str,
    paths: tuple[str, ...],
    stage_size: int = TIERED_STAGE_SIZE,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Chunk normal modules while isolating explicitly split heavy contracts."""

    staged_targets: list[tuple[str | None, tuple[str, ...]]] = []
    pending: list[str] = []

    def flush_pending() -> None:
        if not pending:
            return
        staged_targets.append((None, tuple(pending)))
        pending.clear()

    for path in paths:
        split_names = BOUNDED_MODULE_TEST_SPLITS.get(path)
        if not split_names:
            pending.append(path)
            if len(pending) >= stage_size:
                flush_pending()
            continue

        flush_pending()
        module_name = _module_name(path)
        for index, test_name in enumerate(split_names, start=1):
            staged_targets.append(
                (
                    f"{stage_prefix} isolated {module_name} {index}/{len(split_names)}",
                    (f"{path}::{test_name}",),
                )
            )

    flush_pending()
    ordinary_total = sum(label is None for label, _targets in staged_targets)
    ordinary_index = 0
    stages: list[tuple[str, tuple[str, ...]]] = []
    for label, targets in staged_targets:
        if label is None:
            ordinary_index += 1
            label = (
                stage_prefix
                if ordinary_total == 1
                else f"{stage_prefix} {ordinary_index}/{ordinary_total}"
            )
        stages.append((label, targets))
    return tuple(stages)


def remaining_test_paths(
    repo_root: Path,
    already_covered: set[str] | None = None,
    reserved_for_later: set[str] | None = None,
) -> tuple[str, ...]:
    """Return test modules not covered by the named runner groups yet."""

    covered = set(already_covered or set())
    reserved = set(reserved_for_later or set())
    return tuple(
        f"{TEST_ROOT}/{module}"
        for module in existing_test_modules(repo_root)
        if module not in covered and module not in reserved
    )


def build_full_stages(repo_root: Path) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Build a no-duplicate full-suite plan with readable progress stages."""

    stages: list[tuple[str, tuple[str, ...]]] = []
    covered: set[str] = set()

    for stage_label, group_name, paths in (
        ("fast safety", "fast", FAST_TESTS),
        ("quality", "quality", QUALITY_TESTS),
    ):
        stage_paths = tuple(path for path in paths if _module_name(path) not in covered)
        stage_size = CHUNKED_GROUP_STAGE_SIZES.get(group_name, TIERED_STAGE_SIZE)
        for stage_name, chunk in bounded_group_stages(
            stage_label,
            stage_paths,
            stage_size=stage_size,
        ):
            stages.append((stage_name, chunk))
            covered.update(_module_name(path) for path in chunk)

    reserved_for_later = {
        _module_name(path)
        for path in (*PDF_TESTS, *SLOW_TESTS)
        if _module_name(path) not in covered
    }
    remaining = remaining_test_paths(repo_root, covered, reserved_for_later)
    if remaining:
        chunks = tuple(
            remaining[index : index + REMAINING_STAGE_SIZE]
            for index in range(0, len(remaining), REMAINING_STAGE_SIZE)
        )
        for index, chunk in enumerate(chunks, start=1):
            stages.append((f"remaining non-tiered {index}/{len(chunks)}", chunk))
            covered.update(_module_name(path) for path in chunk)

    stage_paths = tuple(path for path in PDF_TESTS if _module_name(path) not in covered)
    for stage_name, chunk in bounded_group_stages("pdf/rendering", stage_paths, stage_size=PDF_STAGE_SIZE):
        stages.append((stage_name, chunk))
        covered.update(_module_name(path) for path in chunk)

    slow_paths = tuple(path for path in SLOW_TESTS if _module_name(path) not in covered)
    for stage_name, stage_paths in build_slow_stages(slow_paths):
        stages.append((stage_name, stage_paths))
        covered.update(_module_name(path) for path in stage_paths)

    return tuple(stages)


def _expand_slow_targets(paths: tuple[str, ...]) -> tuple[str, ...]:
    if tuple(paths) == SLOW_TESTS:
        return slow_direct_targets()

    root = Path(__file__).resolve().parents[1]
    targets: list[str] = []
    for path in paths:
        explicit_tests = SLOW_TEST_SPLITS.get(path)
        names = explicit_tests or _no_arg_test_function_names(root, path)
        targets.extend(f"{path}::{test_name}" for test_name in names)
    return tuple(targets)


def _target_label(target: str) -> str:
    module, _, test_name = target.partition("::")
    if test_name:
        return f"{_module_name(module)}::{test_name}"
    return _module_name(module)


def build_slow_stages(
    paths: tuple[str, ...] | None = None,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Run slow targets in isolated pytest subprocesses to avoid global state leaks."""

    selected_targets = _expand_slow_targets(tuple(paths or SLOW_TESTS))
    return tuple(
        (f"slow {index}/{len(selected_targets)}: {_target_label(target)}", (target,))
        for index, target in enumerate(selected_targets, start=1)
    )


def focused_group_names() -> tuple[str, ...]:
    """Return non-tiered convenience lanes for targeted patch validation."""

    return tuple(name for name in GROUP_ORDER if name not in {"fast", "quality", "pdf", "slow"})


def group_descriptions() -> dict[str, str]:
    """Return human-readable descriptions for every named test lane."""

    return dict(GROUP_DESCRIPTIONS)




def group_module_names() -> dict[str, set[str]]:
    """Return test module names keyed by runner group."""

    return {name: {_module_name(path) for path in paths} for name, paths in GROUPS.items()}


def module_group_names(module_name: str) -> tuple[str, ...]:
    """Return runner groups that include a test module."""

    groups = group_module_names()
    return tuple(name for name in GROUP_ORDER if module_name in groups[name])


def critical_module_names() -> set[str]:
    return {_module_name(path) for path in CRITICAL_TESTS}


def fast_module_names() -> set[str]:
    return {_module_name(path) for path in FAST_TESTS}


def _no_arg_test_function_names(repo_root: Path, relative_path: str) -> tuple[str, ...]:
    """Return direct-callable no-fixture test functions from a test module."""

    import ast

    tree = ast.parse((repo_root / relative_path).read_text(encoding="utf-8"))
    names = [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name.startswith("test_")
        and not node.args.args
    ]
    return tuple(names)


def slow_direct_targets(repo_root: Path | None = None) -> tuple[str, ...]:
    """Return the exact isolated slow-test targets used by the slow harness."""

    root = repo_root or Path(__file__).resolve().parents[1]
    targets: list[str] = []
    for path in SLOW_TESTS:
        explicit_tests = SLOW_TEST_SPLITS.get(path)
        names = explicit_tests or _no_arg_test_function_names(root, path)
        targets.extend(f"{path}::{name}" for name in names)
    return tuple(targets)


def pdf_module_names() -> set[str]:
    return {_module_name(path) for path in PDF_TESTS}


def slow_module_names() -> set[str]:
    return {_module_name(path) for path in SLOW_TESTS}


def quality_module_names() -> set[str]:
    return {_module_name(path) for path in QUALITY_TESTS} | {
        "test_broad_logic_stress_regressions.py",
        "test_real_fixture_quality_gate.py",
        "test_regressions_fixture_quality.py",
        "test_rendered_pdf_quality.py",
    }
