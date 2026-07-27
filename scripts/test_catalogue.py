"""Validate and list the explicit bounded test catalogue without running tests."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.test_group_catalog import (  # noqa: E402
    EMPTY_LEGACY_TEST_MODULES,
    GROUP_ORDER,
    GROUPS,
    TEST_ROOT,
)


@dataclass(frozen=True, slots=True)
class CatalogueIssue:
    code: str
    message: str
    group: str = ""
    target: str = ""


@dataclass(frozen=True, slots=True)
class TestCatalogueReport:
    discovered_modules: tuple[str, ...]
    registered_modules: tuple[str, ...]
    uncatalogued_modules: tuple[str, ...]
    issues: tuple[CatalogueIssue, ...]

    @property
    def valid(self) -> bool:
        return not self.issues

    def as_dict(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "discovered_modules": list(self.discovered_modules),
            "registered_modules": list(self.registered_modules),
            "uncatalogued_modules": list(self.uncatalogued_modules),
            "issues": [asdict(issue) for issue in self.issues],
        }


def module_path_for_target(target: str) -> str:
    return str(target).partition("::")[0]


def module_name_for_target(target: str) -> str:
    return Path(module_path_for_target(target)).name


def discover_test_modules(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    tests_dir = repo_root / TEST_ROOT
    return tuple(
        path.name
        for path in sorted(tests_dir.glob("test_*.py"))
        if path.name not in EMPTY_LEGACY_TEST_MODULES
    )


def validate_test_catalogue(
    repo_root: Path = REPO_ROOT,
    *,
    groups: Mapping[str, Sequence[str]] | None = None,
    group_order: Sequence[str] | None = None,
) -> TestCatalogueReport:
    """Validate module existence, lane uniqueness, ordering, and coverage."""

    selected_groups = dict(GROUPS if groups is None else groups)
    selected_order = tuple(GROUP_ORDER if group_order is None else group_order)
    issues: list[CatalogueIssue] = []

    if tuple(selected_groups) != selected_order:
        issues.append(
            CatalogueIssue(
                code="group_order_mismatch",
                message="Catalogue group order does not match the registered mapping order.",
            )
        )

    registered_modules: set[str] = set()
    for group_name, targets in selected_groups.items():
        target_values = tuple(str(target) for target in targets)
        if not target_values:
            issues.append(
                CatalogueIssue(
                    code="empty_group",
                    message=f"Test group {group_name!r} has no registered targets.",
                    group=group_name,
                )
            )
            continue

        duplicates = sorted(target for target, count in Counter(target_values).items() if count > 1)
        for target in duplicates:
            issues.append(
                CatalogueIssue(
                    code="duplicate_group_target",
                    message=f"Test group {group_name!r} registers {target!r} more than once.",
                    group=group_name,
                    target=target,
                )
            )

        for target in target_values:
            module_path = module_path_for_target(target)
            module_name = Path(module_path).name
            if not module_path.startswith(f"{TEST_ROOT}/test_") or not module_path.endswith(".py"):
                issues.append(
                    CatalogueIssue(
                        code="invalid_test_target",
                        message=f"Registered target {target!r} is not a first-party test module.",
                        group=group_name,
                        target=target,
                    )
                )
                continue
            if not (repo_root / module_path).is_file():
                issues.append(
                    CatalogueIssue(
                        code="missing_test_module",
                        message=f"Registered test module {module_path!r} does not exist.",
                        group=group_name,
                        target=target,
                    )
                )
                continue
            registered_modules.add(module_name)

    discovered = discover_test_modules(repo_root)
    uncatalogued = tuple(sorted(set(discovered) - registered_modules))
    for module_name in uncatalogued:
        issues.append(
            CatalogueIssue(
                code="uncatalogued_test_module",
                message=f"Active test module {module_name!r} is not registered in any named group.",
                target=f"{TEST_ROOT}/{module_name}",
            )
        )

    return TestCatalogueReport(
        discovered_modules=discovered,
        registered_modules=tuple(sorted(registered_modules)),
        uncatalogued_modules=uncatalogued,
        issues=tuple(issues),
    )


def assert_test_catalogue_valid(repo_root: Path = REPO_ROOT) -> TestCatalogueReport:
    report = validate_test_catalogue(repo_root)
    if report.valid:
        return report
    details = "\n".join(f"- {issue.code}: {issue.message}" for issue in report.issues)
    raise ValueError(f"Invalid bounded test catalogue:\n{details}")


def duplicate_stage_targets(stages: Sequence[object]) -> tuple[str, ...]:
    """Return exact targets registered more than once in one executable plan."""

    targets: list[str] = []
    for stage in stages:
        targets.extend(str(target) for target in getattr(stage, "targets", ()) or ())
    return tuple(sorted(target for target, count in Counter(targets).items() if count > 1))


def assert_unique_stage_targets(stages: Sequence[object]) -> None:
    duplicates = duplicate_stage_targets(stages)
    if duplicates:
        raise ValueError(
            "Executable test plan contains duplicate target registrations:\n"
            + "\n".join(f"- {target}" for target in duplicates)
        )


def catalogue_lines(group_name: str | None = None) -> tuple[str, ...]:
    selected = GROUPS.items() if group_name is None else ((group_name, GROUPS[group_name]),)
    lines: list[str] = []
    for name, targets in selected:
        lines.append(f"{name} ({len(targets)} targets)")
        lines.extend(f"  - {target}" for target in targets)
    return tuple(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or list the bounded test catalogue.")
    parser.add_argument("--list", action="store_true", help="List registrations without running tests.")
    parser.add_argument("--group", choices=GROUP_ORDER)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = validate_test_catalogue(REPO_ROOT)
    if args.list:
        if args.json:
            payload = report.as_dict()
            payload["catalogue"] = {
                name: list(targets)
                for name, targets in GROUPS.items()
                if args.group is None or name == args.group
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print("\n".join(catalogue_lines(args.group)))
            print(
                f"\nCatalogue: {len(report.discovered_modules)} discovered, "
                f"{len(report.registered_modules)} registered, "
                f"{len(report.uncatalogued_modules)} uncatalogued."
            )
    elif args.json:
        print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    else:
        status = "valid" if report.valid else "invalid"
        print(
            f"Bounded test catalogue is {status}: "
            f"{len(report.discovered_modules)} discovered modules, "
            f"{len(report.registered_modules)} registered modules."
        )
        for issue in report.issues:
            print(f"- {issue.code}: {issue.message}")
    return 0 if report.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
