"""Run named pytest groups with readable progress output."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.test_groups import (
    GROUPS,
    GROUP_ORDER,
    HEALTH_CHECK_GROUPS,
    RELEASE_CANDIDATE_GROUPS,
    CHUNKED_GROUP_STAGE_SIZES,
    chunked_group_stages,
    build_full_stages,
    build_slow_stages,
    group_descriptions,
    missing_group_paths,
)

DEFAULT_PYTEST_FLAGS = ("-q", "--durations=10")
DEFAULT_STAGE_TIMEOUT_SECONDS = int(
    os.environ.get("ITINERARY_TEST_STAGE_TIMEOUT_SECONDS", "300")
)
RUNNER_GROUPS = (*GROUP_ORDER, "health", "release", "full")


@dataclass(frozen=True)
class StageRunResult:
    """One pytest stage result for readable timeout diagnostics."""

    label: str
    return_code: int
    elapsed_seconds: float

    @property
    def passed(self) -> bool:
        return self.return_code == 0

    @property
    def timed_out(self) -> bool:
        return self.return_code == 124


def _split_extra_pytest_args(extra_args: list[str]) -> list[str]:
    if extra_args and extra_args[0] == "--":
        return extra_args[1:]
    return extra_args


def _pytest_command(stage_name: str, pytest_args: tuple[str, ...], extra_args: list[str]) -> list[str]:
    stage_flags = ("-s",) if stage_name.startswith("slow ") else ()
    return [sys.executable, "-m", "pytest", *DEFAULT_PYTEST_FLAGS, *stage_flags, *pytest_args, *extra_args]


def _pytest_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    return env


def _process_kwargs() -> dict[str, object]:
    """Return subprocess options for pytest stages."""

    return {}


def _terminate_process_tree(process: subprocess.Popen[object]) -> None:
    """Best-effort cleanup so a timed-out pytest stage cannot hang the runner."""

    try:
        process.kill()
    except Exception:
        return


def _run_command_result(label: str, cmd: list[str], timeout_seconds: int = DEFAULT_STAGE_TIMEOUT_SECONDS, *, env: dict[str, str] | None = None) -> StageRunResult:
    print(f"\n=== {label} ===", flush=True)
    print(" ".join(cmd), flush=True)
    print(f"stage timeout: {timeout_seconds}s", flush=True)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            env=env or _pytest_env(),
            stdin=subprocess.DEVNULL,
            timeout=timeout_seconds or None,
            check=False,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        print(
            f"=== {label}: timed out after {elapsed:.1f}s "
            f"(limit {timeout_seconds}s) ===",
            flush=True,
        )
        print(
            "The timed-out stage was terminated. Run with --plan to see "
            "the exact stage split, or increase ITINERARY_TEST_STAGE_TIMEOUT_SECONDS "
            "for slower machines.",
            flush=True,
        )
        return StageRunResult(label=label, return_code=124, elapsed_seconds=elapsed)

    elapsed = time.monotonic() - started
    return_code = completed.returncode
    status = "passed" if return_code == 0 else f"failed ({return_code})"
    print(f"=== {label}: {status} in {elapsed:.1f}s ===", flush=True)
    return StageRunResult(label=label, return_code=return_code, elapsed_seconds=elapsed)


def _run_command(label: str, cmd: list[str], timeout_seconds: int = DEFAULT_STAGE_TIMEOUT_SECONDS) -> int:
    """Compatibility wrapper returning only the process code."""

    return _run_command_result(label, cmd, timeout_seconds).return_code


def _run_slow_harness() -> int:
    return _run_command("slow direct harness", [sys.executable, "scripts/run_slow_tests.py"])


def _run_pytest(stage_name: str, pytest_args: tuple[str, ...], extra_args: list[str]) -> int:
    return _run_command(stage_name, _pytest_command(stage_name, pytest_args, extra_args))


def _run_pytest_result(stage_name: str, pytest_args: tuple[str, ...], extra_args: list[str]) -> StageRunResult:
    return _run_command_result(stage_name, _pytest_command(stage_name, pytest_args, extra_args))


def _base_stages_for_group(group_name: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if group_name == "slow":
        return build_slow_stages()
    if group_name in CHUNKED_GROUP_STAGE_SIZES:
        return chunked_group_stages(
            group_name,
            GROUPS[group_name],
            stage_size=CHUNKED_GROUP_STAGE_SIZES[group_name],
        )
    return ((group_name, GROUPS[group_name]),)


def _group_sequence_stages(group_names: tuple[str, ...]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    stages: list[tuple[str, tuple[str, ...]]] = []
    for group_name in group_names:
        stages.extend(_base_stages_for_group(group_name))
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

def _child_runner_command(group_name: str, stage_number: int, extra_args: list[str]) -> list[str]:
    """Return a fresh runner command for one stage.

    Running each selected stage through a fresh runner process avoids rare
    interpreter shutdown hangs after PDF/render-heavy pytest subprocesses while
    keeping the normal stage plan and output format.
    """

    cmd = [sys.executable, str(Path(__file__).resolve()), group_name, "--stage-range", str(stage_number)]
    if extra_args:
        cmd.extend(["--", *extra_args])
    return cmd


def _print_stage_summary(results: list[StageRunResult]) -> None:
    """Print a compact summary so wrapper timeouts are easy to diagnose."""

    if not results:
        return
    total = sum(result.elapsed_seconds for result in results)
    print("\n=== Stage summary ===", flush=True)
    for result in results:
        if result.timed_out:
            status = "TIMEOUT"
        elif result.passed:
            status = "PASS"
        else:
            status = f"FAIL({result.return_code})"
        print(f"{status:>9} {result.elapsed_seconds:7.1f}s  {result.label}", flush=True)
    print(f"Total stage runtime: {total:.1f}s", flush=True)

def run_named_group(group_name: str, extra_args: list[str], *, stage_range: str | None = None) -> int:
    missing = missing_group_paths(REPO_ROOT)
    if missing:
        print("Configured test group paths are missing:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 2

    if group_name == "slow" and not extra_args:
        return _run_slow_harness()

    stages = _stages_for_group(group_name)
    try:
        stage_slice = _parse_stage_range(stage_range, len(stages))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    selected_stages = stages[stage_slice]
    selected_indices = list(range(1, len(stages) + 1))[stage_slice]

    if group_name in {"health", "release", "full"}:
        print(f"{group_name.title()} suite plan: {len(stages)} progress-tracked stages", flush=True)
    if stage_range:
        print(f"Running stage range {stage_range}: {len(selected_stages)} of {len(stages)} stages", flush=True)

    # Parent runner: delegate multi-stage ranges to fresh runner processes. This
    # keeps long validation lanes resilient when a render/PDF-heavy pytest
    # subprocess leaves shutdown work behind after reporting test success.
    if len(selected_stages) > 1 and not os.environ.get("ITINERARY_TEST_RUNNER_CHILD"):
        results: list[StageRunResult] = []
        for stage_number, (stage_name, _pytest_paths) in zip(selected_indices, selected_stages):
            env = _pytest_env()
            env["ITINERARY_TEST_RUNNER_CHILD"] = "1"
            result = _run_command_result(
                f"{stage_name} runner",
                _child_runner_command(group_name, stage_number, extra_args),
                timeout_seconds=DEFAULT_STAGE_TIMEOUT_SECONDS + 60,
                env=env,
            )
            results.append(result)
            if result.return_code != 0:
                _print_stage_summary(results)
                return result.return_code
        _print_stage_summary(results)
        return 0

    results: list[StageRunResult] = []
    for stage_name, pytest_paths in selected_stages:
        result = _run_pytest_result(stage_name, tuple(pytest_paths), extra_args)
        results.append(result)
        if result.return_code != 0:
            _print_stage_summary(results)
            return result.return_code
    _print_stage_summary(results)
    return 0



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


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    pulled_stage_range, raw_args = _pull_stage_range(raw_args)
    runner_args, list_groups, plan = _extract_runner_flags(raw_args)

    parser = argparse.ArgumentParser(
        description="Run Itinerary App pytest groups with progress by suite bucket."
    )
    parser.add_argument(
        "group",
        nargs="?",
        choices=RUNNER_GROUPS,
        help="Named test group to run.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Optional extra pytest args. Use -- before pytest flags, e.g. -- -k parser.",
    )
    parser.add_argument(
        "--list-groups",
        action="store_true",
        help="Show available groups and exit without running pytest.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Show the selected group's staged pytest plan without running it.",
    )
    parser.add_argument(
        "--stage-range",
        default="",
        help="Run a one-based inclusive stage range such as 1:8 or 9:17.",
    )
    args = parser.parse_args(runner_args)

    if list_groups:
        _print_available_groups()
        return 0

    if not args.group:
        parser.error("the following arguments are required: group unless --list-groups is used")

    if plan:
        _print_group_plan(args.group)
        return 0

    return run_named_group(args.group, _split_extra_pytest_args(args.pytest_args), stage_range=args.stage_range or pulled_stage_range)


if __name__ == "__main__":
    exit_code = main()
    # Pytest/render-heavy stages can leave non-daemon cleanup work behind after
    # the runner has already printed a PASS/FAIL summary.  Flush explicitly and
    # terminate the process so validation wrappers do not hang during Python
    # interpreter shutdown.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
