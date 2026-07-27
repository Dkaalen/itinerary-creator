"""Execute one pytest stage with pre-timeout stack diagnostics."""

from __future__ import annotations

import argparse
import faulthandler
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.test_group_catalog import TEST_STAGE_BOUNDARY_SECONDS


def _split_args(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" not in argv:
        return argv, []
    index = argv.index("--")
    return argv[:index], argv[index + 1 :]


def main(argv: list[str] | None = None) -> int:
    runner_args, pytest_args = _split_args(list(sys.argv[1:] if argv is None else argv))
    parser = argparse.ArgumentParser(description="Run one diagnostic pytest stage.")
    parser.add_argument("--timeout-seconds", type=int, required=True)
    parser.add_argument("--label", default="pytest stage")
    args = parser.parse_args(runner_args)
    args.timeout_seconds = max(1, min(args.timeout_seconds, TEST_STAGE_BOUNDARY_SECONDS))

    os.environ.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("PYTHONFAULTHANDLER", "1")
    faulthandler.enable(all_threads=True)
    diagnostic_delay = max(1, args.timeout_seconds - min(15, max(3, args.timeout_seconds // 5)))
    faulthandler.dump_traceback_later(diagnostic_delay, repeat=False, exit=False)

    print(
        f"pytest stage worker: {args.label} "
        f"(stack dump scheduled at {diagnostic_delay}s; hard limit {args.timeout_seconds}s)",
        flush=True,
    )
    try:
        import pytest

        code = int(pytest.main(pytest_args))
    finally:
        faulthandler.cancel_dump_traceback_later()
        sys.stdout.flush()
        sys.stderr.flush()
    return code


if __name__ == "__main__":
    exit_code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
