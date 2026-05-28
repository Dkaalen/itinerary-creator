import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.rendered_pdf_quality import assert_expectation, expectation_files, load_expectation, render_fixture_pdf_text


def test_rendered_pdf_fixture_expectations():
    files = expectation_files()
    if not files:
        raise AssertionError("No rendered PDF expectation files found.")

    failures = []
    for expectation_path in files:
        expectation = load_expectation(expectation_path)
        try:
            rendered_text = render_fixture_pdf_text(expectation["fixture"])
            assert_expectation(expectation, rendered_text)
        except Exception as exc:  # collect all fixture failures before failing
            failures.append(f"{expectation_path.name}: {exc}")

    if failures:
        raise AssertionError("Rendered PDF quality failures:\n\n" + "\n\n".join(failures))


def run_all():
    test_rendered_pdf_fixture_expectations()
    print(f"All rendered PDF quality tests passed ({len(expectation_files())} fixtures).")


if __name__ == "__main__":
    run_all()
