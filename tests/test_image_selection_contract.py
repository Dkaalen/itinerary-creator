from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from images.day_image_selection import select_day_images_with_overrides
from images.metadata import ImageCandidate
from images.matcher_selection import select_best_candidate_for_context
from images.preview_image_contract import merge_preview_image_contract
from images.selection_commit import SELECTION_COMMIT_KEY


def _row(day: str, city: str = "Oslo", title: str = "Oslo walking tour") -> dict:
    return {"day": day, "city": city, "title": title, "details": title, "date": "15.07.2027"}


def test_equal_candidates_select_same_path_when_input_order_reverses(tmp_path):
    left = tmp_path / "a" / "Oslo_Summer_City.jpg"
    right = tmp_path / "b" / "Oslo_Summer_City.jpg"
    left.parent.mkdir(parents=True)
    right.parent.mkdir(parents=True)
    left.write_bytes(b"a")
    right.write_bytes(b"b")
    candidates = [
        ImageCandidate(str(left), "Norway", "Oslo", left.name, ("oslo", "summer", "city"), ("city",), ("summer",)),
        ImageCandidate(str(right), "Norway", "Oslo", right.name, ("oslo", "summer", "city"), ("city",), ("summer",)),
    ]
    context = {"city": "Oslo", "city_variants": {"oslo"}, "country": "Norway", "themes": {"city"}, "tokens": {"oslo", "walking", "tour"}, "season": "summer"}

    first = select_best_candidate_for_context("Day 1", context, candidates)
    second = select_best_candidate_for_context("Day 1", context, list(reversed(candidates)))

    assert first and second
    assert first["path"] == second["path"]


def test_manual_image_can_be_deliberately_reused_and_commit_survives_copy(tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    manual = tmp_path / "chosen.jpg"
    manual.write_bytes(b"manual")
    grouped = {"Day 1": [_row("Day 1")], "Day 2": [_row("Day 2")]}
    edits = {
        "day_images": {
            "Day 1": {"mode": "manual", "path": str(manual)},
            "Day 2": {"mode": "manual", "path": str(manual)},
        }
    }

    matches = select_day_images_with_overrides(grouped, edits, app_root=tmp_path, image_bank_scan_paths=[bank])

    assert matches["Day 1"]["path"] == matches["Day 2"]["path"]
    assert matches["Day 1"]["duplicate_policy"] == "unique"
    assert matches["Day 2"]["duplicate_policy"] == "intentional_manual_reuse"
    assert matches["Day 2"]["user_override"] is True
    restored = deepcopy(edits)
    assert restored[SELECTION_COMMIT_KEY]["matches"]["Day 2"]["duplicate_policy"] == "intentional_manual_reuse"


def test_valid_commit_is_reused_and_matching_fact_change_invalidates(monkeypatch, tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    image = bank / "Oslo_Summer_City.jpg"
    image.write_bytes(b"image")
    grouped = {"Day 1": [_row("Day 1")]}
    edits = {}
    calls = {"count": 0}

    def fake_select(grouped_days, image_bank_paths, used_paths=None):
        calls["count"] += 1
        return {"Day 1": {"day": "Day 1", "path": str(image), "filename": image.name, "score": 10, "reason": "test match", "score_breakdown": {"total_score": 10}}}

    monkeypatch.setattr("images.day_image_selection.select_day_images", fake_select)
    first = select_day_images_with_overrides(grouped, edits, app_root=tmp_path, image_bank_scan_paths=[bank])
    second = select_day_images_with_overrides(grouped, edits, app_root=tmp_path, image_bank_scan_paths=[bank])
    assert calls["count"] == 1
    assert first == second

    changed = {"Day 1": [_row("Day 1", title="Oslofjord cruise")]}
    select_day_images_with_overrides(changed, edits, app_root=tmp_path, image_bank_scan_paths=[bank])
    assert calls["count"] == 2


def test_preview_bytes_only_enrich_same_committed_path(tmp_path):
    selected_path = tmp_path / "selected.jpg"
    stale_path = tmp_path / "stale.jpg"
    selected = {"Day 1": {"path": str(selected_path), "reason": "manual", "user_override": True}}
    stale = {"Day 1": {"path": str(stale_path), "data_uri": "data:image/jpeg;base64,STALE"}}

    merged = merge_preview_image_contract(selected, stale)
    assert merged["Day 1"]["path"] == str(selected_path)
    assert "data_uri" not in merged["Day 1"]

    matching = {"Day 1": {"path": str(selected_path), "data_uri": "data:image/jpeg;base64,CURRENT"}}
    enriched = merge_preview_image_contract(selected, matching)
    assert enriched["Day 1"]["data_uri"].endswith("CURRENT")


def test_explicit_removal_beats_stale_preview(tmp_path):
    preview = {"Day 3": {"path": str(tmp_path / "old.jpg"), "data_uri": "data:image/jpeg;base64,OLD"}}
    merged = merge_preview_image_contract({"Day 3": None}, preview, removed_days={"Day 3"})
    assert merged["Day 3"] is None
