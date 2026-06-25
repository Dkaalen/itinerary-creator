"""Compatibility CLI for rebuilding the versioned reference corpus."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0, str(PROJECT_ROOT))

from scripts.reference_corpus_build.cli import main
from scripts.reference_corpus_build.common import CORPUS_VERSION, SCHEMA_VERSION, TARGET_ICELAND_SHEETS
from scripts.reference_corpus_build.manifest import build_manifest
from scripts.reference_corpus_build.tabular import build_clean_activities, build_standard_templates
from scripts.reference_corpus_build.xlsx import build_iceland_reference

__all__ = ["CORPUS_VERSION", "SCHEMA_VERSION", "TARGET_ICELAND_SHEETS", "build_clean_activities", "build_iceland_reference", "build_manifest", "build_standard_templates", "main"]

if __name__ == "__main__": raise SystemExit(main())
