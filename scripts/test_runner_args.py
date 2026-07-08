"""Argument parsing helpers for scripts.run_test_group."""

from __future__ import annotations


def _split_extra_pytest_args(extra_args: list[str]) -> list[str]:
    if extra_args and extra_args[0] == "--":
        return extra_args[1:]
    return extra_args


def _parse_stage_range(value: str | None, stage_count: int) -> slice:
    """Return a one-based inclusive stage slice for resumable wrapper runs."""

    if not value:
        return slice(None)
    text = str(value).strip()
    if not text:
        return slice(None)
    if ":" in text:
        start_text, _, end_text = text.partition(":")
        start = int(start_text) if start_text else 1
        end = int(end_text) if end_text else stage_count
    else:
        start = end = int(text)
    if start < 1 or end < start or end > stage_count:
        raise ValueError(f"Invalid --stage-range {value!r}; use 1:{stage_count}.")
    return slice(start - 1, end)


def _pull_stage_range(argv: list[str]) -> tuple[str, list[str]]:
    """Remove runner-only --stage-range before pytest passthrough parsing."""

    if "--" in argv:
        boundary = argv.index("--")
        runner_side = argv[:boundary]
        pytest_side = argv[boundary:]
    else:
        runner_side = argv
        pytest_side = []

    cleaned: list[str] = []
    value = ""
    index = 0
    while index < len(runner_side):
        item = runner_side[index]
        if item == "--stage-range":
            if index + 1 >= len(runner_side):
                value = ""
            else:
                value = runner_side[index + 1]
                index += 2
                continue
        elif item.startswith("--stage-range="):
            value = item.split("=", 1)[1]
            index += 1
            continue
        cleaned.append(item)
        index += 1
    return value, [*cleaned, *pytest_side]


def _extract_runner_flags(argv: list[str]) -> tuple[list[str], bool, bool]:
    """Pull runner flags out before pytest passthrough args consume them."""

    if "--" in argv:
        separator_index = argv.index("--")
        runner_side = argv[:separator_index]
        pytest_side = argv[separator_index:]
    else:
        runner_side = argv
        pytest_side = []

    list_groups = "--list-groups" in runner_side
    plan = "--plan" in runner_side
    remaining = [arg for arg in runner_side if arg not in {"--list-groups", "--plan"}]
    return [*remaining, *pytest_side], list_groups, plan
