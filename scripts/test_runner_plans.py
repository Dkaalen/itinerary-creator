"""Stage-plan helpers for scripts.run_test_group."""

from __future__ import annotations

from pathlib import Path

from scripts.test_groups import (
    GROUPS,
    GROUP_ORDER,
    HEALTH_CHECK_GROUPS,
    RELEASE_CANDIDATE_GROUPS,
    CHUNKED_GROUP_STAGE_SIZES,
    chunked_group_stages,
    bounded_group_stages,
    build_full_stages,
    build_slow_stages,
    group_descriptions,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_GROUPS = (*GROUP_ORDER, "health", "release", "full")


def _base_stages_for_group(group_name: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if group_name == "slow":
        return build_slow_stages()
    if group_name in CHUNKED_GROUP_STAGE_SIZES:
        return bounded_group_stages(
            group_name,
            GROUPS[group_name],
            stage_size=CHUNKED_GROUP_STAGE_SIZES[group_name],
        )
    return ((group_name, GROUPS[group_name]),)


def _group_sequence_stages(group_names: tuple[str, ...]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Compose overlapping domain lanes without re-running exact targets."""

    stages: list[tuple[str, tuple[str, ...]]] = []
    registered_targets: set[str] = set()
    for group_name in group_names:
        for stage_name, targets in _base_stages_for_group(group_name):
            unique_targets = tuple(target for target in targets if target not in registered_targets)
            if not unique_targets:
                continue
            stages.append((stage_name, unique_targets))
            registered_targets.update(unique_targets)
    return tuple(stages)


def _stages_for_group(group_name: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if group_name == "full":
        return build_full_stages(REPO_ROOT)
    if group_name == "health":
        return _group_sequence_stages(HEALTH_CHECK_GROUPS)
    if group_name == "release":
        return _group_sequence_stages(RELEASE_CANDIDATE_GROUPS)
    return _base_stages_for_group(group_name)


def _print_group_plan(group_name: str) -> None:
    descriptions = group_descriptions()
    stages = _stages_for_group(group_name)
    print(f"{group_name}: {descriptions.get(group_name, 'progress-tracked full validation')}")
    print(f"Stages: {len(stages)}")
    for index, (stage_name, pytest_paths) in enumerate(stages, start=1):
        print(f"  {index:02d}. {stage_name} ({len(pytest_paths)} target{'s' if len(pytest_paths) != 1 else ''})")
        for path in pytest_paths:
            print(f"      - {path}")


def _print_available_groups() -> None:
    descriptions = group_descriptions()
    print("Available test groups:")
    for name in RUNNER_GROUPS:
        description = descriptions.get(name, "progress-tracked full validation")
        print(f"  {name:12} {description}")
