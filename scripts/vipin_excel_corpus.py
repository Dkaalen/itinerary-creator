"""Compatibility facade for the responsibility-split Vipin Excel corpus runner."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.vipin_corpus import *  # noqa: F401,F403,E402
from scripts.vipin_corpus.cli import main  # noqa: E402,F401


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
