"""Generate extracted PDF text for real-input fixtures for manual review.

Usage:
    python tests/tools/generate_fixture_pdf_texts.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tests.rendered_pdf_quality import EXPECTATIONS_DIR, load_expectation, render_fixture_pdf_text

OUT_DIR = ROOT / "outputs" / "fixture_pdf_text"
OUT_DIR.mkdir(parents=True, exist_ok=True)

for expectation_path in sorted(EXPECTATIONS_DIR.glob("*.json")):
    expectation = load_expectation(expectation_path)
    text = render_fixture_pdf_text(expectation["fixture"])
    output_path = OUT_DIR / f"{expectation_path.stem}.txt"
    output_path.write_text(text, encoding="utf-8")
    print(f"Wrote {output_path.relative_to(ROOT)}")
