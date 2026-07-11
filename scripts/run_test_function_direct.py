"""Run one no-fixture test function and terminate without pytest teardown."""

from __future__ import annotations

import argparse
import faulthandler
import importlib.util
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _finish(code: int) -> None:
    faulthandler.cancel_dump_traceback_later()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run one no-fixture test function directly.")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("test_file")
    parser.add_argument("test_function")
    args = parser.parse_args(argv or sys.argv[1:])

    os.environ.setdefault("PYTHONFAULTHANDLER", "1")
    faulthandler.enable(all_threads=True)
    diagnostic_delay = max(1, args.timeout_seconds - min(15, max(3, args.timeout_seconds // 5)))
    faulthandler.dump_traceback_later(diagnostic_delay, repeat=False, exit=False)

    path = REPO_ROOT / args.test_file
    try:
        spec = importlib.util.spec_from_file_location("direct_test_module", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not import {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        test_func = getattr(module, args.test_function)
        test_func()
    except Exception:
        traceback.print_exc()
        _finish(1)
    _finish(0)


if __name__ == "__main__":
    main()
