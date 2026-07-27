from __future__ import annotations

import json
from pathlib import Path

from scripts.module_ownership_audit import iter_python_files
from scripts.report_fingerprints import build_report_fingerprint, python_source_tree_fingerprint


ROOT = Path(__file__).resolve().parents[1]
REPORTS = (
    ROOT / "docs/reports/module_ownership_audit/latest.json",
    ROOT / "docs/reports/deletion_candidates/latest.json",
)
RETIRED_OWNER_PATHS = (
    "itinerary_generation/client_copy_sanitation.py",
    "itinerary_generation/client_sanitizer.py",
    "itinerary_generation/clipboard_sanitizer.py",
    "itinerary_generation/supplier_cleanup_brain.py",
    "pdf_exporter_modules/public_api.py",
)


def test_python_source_tree_fingerprint_is_deterministic_and_content_sensitive(tmp_path: Path) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text("VALUE = 1\n", encoding="utf-8")
    second.write_text("VALUE = 2\n", encoding="utf-8")

    original = python_source_tree_fingerprint(tmp_path, (second, first))
    repeated = python_source_tree_fingerprint(tmp_path, (first, second))
    second.write_text("VALUE = 3\n", encoding="utf-8")
    changed = python_source_tree_fingerprint(tmp_path, (first, second))

    assert original == repeated
    assert original[0].startswith("sha256:")
    assert original[1] == 2
    assert changed != original


def test_latest_architecture_reports_match_the_current_python_source_tree() -> None:
    expected = build_report_fingerprint(ROOT, iter_python_files(ROOT))

    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in REPORTS]
    fingerprints = [payload["report_fingerprint"] for payload in payloads]

    assert fingerprints[0] == fingerprints[1]
    recorded = fingerprints[0]
    assert recorded["python_source_tree_sha256"] == expected.python_source_tree_sha256
    assert recorded["python_source_file_count"] == expected.python_source_file_count
    assert recorded["repository_head"]
    assert recorded["repository_head_tree"]

    # A report generated from a clean checkout must identify that exact Git
    # state. Reports generated before a commit deliberately record a dirty
    # baseline; their portable source-tree hash remains the freshness proof in
    # a later commit or source-only delivery extraction.
    if expected.repository_head and recorded["working_tree_clean"]:
        assert recorded["repository_head"] == expected.repository_head
        assert recorded["repository_head_tree"] == expected.repository_head_tree
    assert expected.python_source_file_count >= 1_000


def test_latest_architecture_reports_do_not_reference_retired_owner_paths() -> None:
    report_text = "\n".join(
        path.read_text(encoding="utf-8")
        for report_dir in (
            ROOT / "docs/reports/module_ownership_audit",
            ROOT / "docs/reports/deletion_candidates",
        )
        for path in sorted(report_dir.glob("latest.*"))
    )

    assert all(path not in report_text for path in RETIRED_OWNER_PATHS)
    assert "## Repository fingerprint" in report_text
    assert "Audited Python source tree" in report_text
