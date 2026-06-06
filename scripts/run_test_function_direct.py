"""Run one no-fixture test function and terminate without pytest teardown."""

from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _finish(code: int) -> None:
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)


def main(argv: list[str] | None = None) -> None:
    args = list(argv or sys.argv[1:])
    if len(args) != 2:
        print("Usage: run_test_function_direct.py <test-file> <test-function>", file=sys.stderr)
        _finish(2)

    relative_path, test_name = args
    path = REPO_ROOT / relative_path
    try:
        spec = importlib.util.spec_from_file_location("direct_test_module", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not import {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        test_func = getattr(module, test_name)
        test_func()
    except Exception:
        traceback.print_exc()
        _finish(1)
    _finish(0)


if __name__ == "__main__":
    main()
