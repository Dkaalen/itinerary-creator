from pathlib import Path


ACTIVITY_FIXTURE_DIR = Path("tests/fixtures/activity_training")
TEXT_FIXTURES = [
    ACTIVITY_FIXTURE_DIR / "cleaned_activity_master.tsv",
    ACTIVITY_FIXTURE_DIR / "raw_messy_activity_source.txt",
]


def test_activity_training_fixtures_use_lf_line_endings() -> None:
    for fixture_path in TEXT_FIXTURES:
        data = fixture_path.read_bytes()
        assert b"\r\n" not in data, f"{fixture_path} must use LF line endings"


def test_cleaned_activity_master_has_expected_tsv_header() -> None:
    header = (ACTIVITY_FIXTURE_DIR / "cleaned_activity_master.tsv").read_text(
        encoding="utf-8"
    ).splitlines()[0]
    assert header == "Type\tCity\tActivity"
