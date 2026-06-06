from __future__ import annotations

import zipfile
from pathlib import Path

from PIL import Image

from images import image_bank
from images.matcher_selection import select_day_image


def _write_webp(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 20), (20, 80, 120)).save(path, format="WEBP")


def _write_image_bank_zip(zip_path: Path) -> None:
    source_root = zip_path.parent / "zip-source" / "itinerary-image-bank-main"
    _write_webp(source_root / "image_bank_full" / "Norway" / "Oslo" / "Oslo_Autumn_City_01.webp")
    with zipfile.ZipFile(zip_path, "w") as archive:
        for path in source_root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(zip_path.parent / "zip-source"))


def test_patch_au_remote_zip_connector_installs_separate_image_bank_when_git_is_missing(monkeypatch, tmp_path):
    root = tmp_path / "itinerary-creator-git"
    fallback = root / "image_bank" / "Default"
    _write_webp(fallback / "Default_Autumn_City_01.webp")

    def fake_urlretrieve(url, filename):
        assert "Dkaalen/itinerary-image-bank" in url
        assert url.endswith("/archive/refs/heads/main.zip")
        _write_image_bank_zip(Path(filename))
        return filename, None

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    monkeypatch.setattr(image_bank.shutil, "which", lambda _name: None)
    monkeypatch.setattr(image_bank.urllib.request, "urlretrieve", fake_urlretrieve)

    status = image_bank.connect_remote_image_bank_if_missing(root)

    assert status["full_bank_found"] is True
    assert status["setup_status"]["code"] == "fetched_zip"
    assert status["setup_status"]["method"] == "zip"
    assert "itinerary-image-bank" in status["repo_url"]
    assert image_bank.get_image_bank_paths(root)[0] == root / image_bank.RUNTIME_IMAGE_BANK_DIR / "itinerary-image-bank" / "image_bank_full"


def test_patch_au_remote_bank_beats_bundled_default_after_connection(monkeypatch, tmp_path):
    root = tmp_path / "itinerary-creator-git"
    _write_webp(root / "image_bank" / "Default" / "Default_Autumn_City_01.webp")

    def fake_urlretrieve(url, filename):
        _write_image_bank_zip(Path(filename))
        return filename, None

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    monkeypatch.setattr(image_bank.shutil, "which", lambda _name: None)
    monkeypatch.setattr(image_bank.urllib.request, "urlretrieve", fake_urlretrieve)

    image_bank.connect_remote_image_bank_if_missing(root)
    match = select_day_image(
        "Day 1",
        [{"day": "Day 1", "date": "05/11/2026", "city": "Oslo", "title": "Oslo Walking Tour", "details": "Autumn city walk."}],
        image_bank.get_image_bank_scan_paths(root),
    )

    assert match
    assert match["is_default"] is False
    assert "Norway" in str(match["path"])
    assert "Oslo" in str(match["path"])


def test_patch_au_image_status_message_points_to_separate_remote_repo(tmp_path):
    bank = tmp_path / "image_bank" / "Default"
    _write_webp(bank / "Default_Autumn_City_01.webp")

    status = image_bank.image_bank_status_for_paths([tmp_path / "image_bank"])

    assert status["missing_full_bank"] is True
    assert "separate Dkaalen/itinerary-image-bank repository" in status["blocking_message"]
    assert status["repo_url"].endswith("Dkaalen/itinerary-image-bank.git")
    assert status["zip_url"].endswith("/archive/refs/heads/main.zip")


def test_patch_au_same_destination_selection_prioritizes_season_before_activity_noise(tmp_path):
    bank = tmp_path / "image_bank_full"
    oslo = bank / "Norway" / "Oslo"
    _write_webp(oslo / "Oslo_Autumn_Quiet_Street_01.webp")
    _write_webp(oslo / "Oslo_Walking_Waterfront_Mountain_Fjord_Train_City_01.webp")

    match = select_day_image(
        "Day 1",
        [
            {
                "day": "Day 1",
                "date": "05/11/2026",
                "city": "Oslo",
                "title": "Oslo walking waterfront mountain fjord train city experience",
                "details": "Guided walking tour by the waterfront with city landmarks.",
            }
        ],
        bank,
    )

    assert match
    assert "Autumn" in Path(match["path"]).name
    breakdown = match["score_breakdown"]
    assert breakdown["destination_score"] > 0
    assert breakdown["season_score"] > 0
