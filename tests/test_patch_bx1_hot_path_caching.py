from __future__ import annotations

from pathlib import Path

from images.matcher_context import build_day_context
from images.scanner import get_image_bank_index, invalidate_image_bank_cache, scan_image_bank
from itinerary_generation.activity_products import (
    activity_product_cache_info,
    clear_activity_product_cache,
    fingerprint_activity,
)
from itinerary_generation.product_rules import (
    clear_product_rule_cache,
    find_product_match,
    product_rule_cache_info,
)


def _image(bank: Path, country: str, city: str, name: str) -> Path:
    path = bank / country / city / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"image")
    return path


def test_activity_fingerprint_cache_reuses_equal_source_rows():
    clear_activity_product_cache()
    row = {
        "city": "Alta",
        "title": "Whale Watching & Arctic Wildlife Safari by RIB Boat",
        "details": "RIB boat trip with a certified driver and warm thermal suits",
    }

    first = fingerprint_activity(row)
    second = fingerprint_activity(dict(row))

    assert first == second
    info = activity_product_cache_info()
    assert info.misses == 1
    assert info.hits == 1




def test_product_rule_cache_reuses_equal_source_rows():
    clear_product_rule_cache()
    row = {
        "city": "Tromsø",
        "title": "Northern Lights Safari to Aurora Basecamp",
        "details": "English-speaking guide and coach transport",
    }

    assert find_product_match(row) == find_product_match(dict(row))
    info = product_rule_cache_info()
    assert info.misses == 1
    assert info.hits == 1


def test_activity_fingerprint_cache_invalidates_when_source_content_changes():
    clear_activity_product_cache()
    first = fingerprint_activity({"city": "Alta", "title": "Whale Watching by RIB Boat"})
    second = fingerprint_activity({"city": "Alta", "title": "Northern Lights Safari"})

    assert first != second
    assert activity_product_cache_info().misses == 2


def test_image_bank_index_skips_recursive_rescan_for_hot_cache(monkeypatch, tmp_path):
    bank = tmp_path / "image_bank_full"
    _image(bank, "Norway", "Oslo", "Oslo_Autumn_City_01.webp")
    invalidate_image_bank_cache()

    from images import scanner

    calls = 0
    original = scanner._scan_cache_key

    def counted(paths):
        nonlocal calls
        calls += 1
        return original(paths)

    monkeypatch.setattr(scanner, "_scan_cache_key", counted)

    assert len(scan_image_bank(bank)) == 1
    assert len(scan_image_bank(bank)) == 1
    assert len(get_image_bank_index(bank).candidates) == 1
    assert calls == 1


def test_image_bank_upload_invalidation_refreshes_index(tmp_path):
    bank = tmp_path / "image_bank_full"
    _image(bank, "Norway", "Oslo", "Oslo_Autumn_City_01.webp")
    invalidate_image_bank_cache()
    assert len(scan_image_bank(bank)) == 1

    _image(bank, "Norway", "Bergen", "Bergen_Autumn_Waterfront_01.webp")
    # App-managed uploads call this explicitly; the next read must see the file.
    invalidate_image_bank_cache(bank)
    assert len(scan_image_bank(bank)) == 2


def test_image_bank_context_bucket_contains_only_destination_and_defaults(tmp_path):
    bank = tmp_path / "image_bank_full"
    oslo = _image(bank, "Norway", "Oslo", "Oslo_Autumn_City_01.webp")
    _image(bank, "Norway", "Bergen", "Bergen_Autumn_Waterfront_01.webp")
    default = bank / "Default" / "Default_Autumn_City_01.webp"
    default.parent.mkdir(parents=True, exist_ok=True)
    default.write_bytes(b"image")
    invalidate_image_bank_cache()

    index = get_image_bank_index(bank)
    context = build_day_context("Day 1", [{"type": "Hotel", "city": "Oslo", "date": "01/10/2026"}])
    candidate_paths = {Path(candidate.path) for candidate in index.candidates_for_context(context)}

    assert oslo in candidate_paths
    assert default in candidate_paths
    assert all("Bergen" not in str(path) for path in candidate_paths)
