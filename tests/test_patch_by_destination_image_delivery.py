from __future__ import annotations

from io import BytesIO
from pathlib import Path
import hashlib
import json
import zipfile

from images import image_bank
from images.remote_distribution import (
    DestinationRequest,
    active_distribution_bank,
    destination_requests_from_rows,
    ensure_destination_packs,
)


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._stream = BytesIO(payload)

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stream.close()
        return False


def _pack_bytes(country: str, destination: str, filename: str | None = None) -> bytes:
    stream = BytesIO()
    filename = filename or f"{destination}_Autumn_City_01.webp"
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"image_bank_full/{country}/{destination}/{filename}", b"webp-placeholder")
    return stream.getvalue()


def _manifest_entry(country: str, destination: str, payload: bytes) -> dict:
    asset_name = f"{country.lower()}__{destination.lower().replace('ø', 'o')}.zip"
    return {
        "country": country,
        "destination": destination,
        "country_aliases": [country],
        "destination_aliases": [destination, destination.replace("ø", "o")],
        "asset_name": asset_name,
        "download_url": f"https://example.test/{asset_name}",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "file_count": 1,
    }


def _manifest(entries: dict[str, dict]) -> bytes:
    return json.dumps({
        "schema_version": 1,
        "bank_version": "test-bank-v1",
        "generated_at": "2026-06-15T00:00:00Z",
        "source_commit": "abc123",
        "destinations": entries,
    }).encode("utf-8")


def _url(request) -> str:
    return getattr(request, "full_url", str(request))


def test_patch_by_requests_use_the_same_primary_city_as_day_image_matching():
    requests = destination_requests_from_rows({
        "Day 1": [
            {"day": "Day 1", "type": "Transfer", "city": "Oslo", "title": "Train Oslo to Alta"},
            {"day": "Day 1", "type": "Hotel", "city": "Alta", "title": "Canyon Hotell"},
        ],
        "Day 2": [
            {"day": "Day 2", "type": "Activity", "city": "Tromso", "title": "Northern Lights Safari"},
        ],
    })

    assert [(item.country, item.destination) for item in requests] == [
        ("Norway", "Alta"),
        ("Norway", "Tromsø"),
    ]


def test_patch_by_downloads_only_requested_destination_packs_and_reuses_cache(monkeypatch, tmp_path):
    oslo = _pack_bytes("Norway", "Oslo")
    tromso = _pack_bytes("Norway", "Tromsø")
    bergen = _pack_bytes("Norway", "Bergen")
    entries = {
        "Norway/Oslo": _manifest_entry("Norway", "Oslo", oslo),
        "Norway/Tromsø": _manifest_entry("Norway", "Tromsø", tromso),
        "Norway/Bergen": _manifest_entry("Norway", "Bergen", bergen),
    }
    manifest = _manifest(entries)
    payloads = {
        "manifest.json": manifest,
        entries["Norway/Oslo"]["asset_name"]: oslo,
        entries["Norway/Tromsø"]["asset_name"]: tromso,
        entries["Norway/Bergen"]["asset_name"]: bergen,
    }
    calls: list[str] = []

    def fake_urlopen(request, timeout=None):
        url = _url(request)
        calls.append(url)
        name = url.rsplit("/", 1)[-1]
        return _FakeResponse(payloads[name])

    monkeypatch.setenv("ITINERARY_IMAGE_BANK_MANIFEST_URL", "https://example.test/manifest.json")
    monkeypatch.setattr("images.remote_distribution.urllib.request.urlopen", fake_urlopen)

    result = ensure_destination_packs(
        tmp_path,
        [DestinationRequest("Oslo", "Norway"), DestinationRequest("Tromso", "Norway")],
    )

    assert result["ok"] is True
    assert result["code"] == "destination_packs_ready"
    assert len([url for url in calls if url.endswith(".zip")]) == 2
    assert not any(entries["Norway/Bergen"]["asset_name"] in url for url in calls)

    bank = active_distribution_bank(tmp_path)
    assert bank is not None
    assert any((bank / "Norway" / "Oslo").glob("*.webp"))
    assert any((bank / "Norway" / "Tromsø").glob("*.webp"))
    assert not (bank / "Norway" / "Bergen").exists()

    calls.clear()

    def no_network(request, timeout=None):  # pragma: no cover - failure explains regression
        raise AssertionError(f"Warm destination cache unexpectedly used network: {_url(request)}")

    monkeypatch.setattr("images.remote_distribution.urllib.request.urlopen", no_network)
    warm = ensure_destination_packs(
        tmp_path,
        [DestinationRequest("Oslo", "Norway"), DestinationRequest("Tromsø", "Norway")],
    )
    assert warm["ok"] is True
    assert warm["manifest_source"] == "cache"


def test_patch_by_checksum_failure_never_activates_corrupt_pack(monkeypatch, tmp_path):
    oslo = _pack_bytes("Norway", "Oslo")
    entry = _manifest_entry("Norway", "Oslo", oslo)
    entry["sha256"] = "0" * 64
    manifest = _manifest({"Norway/Oslo": entry})

    def fake_urlopen(request, timeout=None):
        return _FakeResponse(manifest if _url(request).endswith("manifest.json") else oslo)

    monkeypatch.setenv("ITINERARY_IMAGE_BANK_MANIFEST_URL", "https://example.test/manifest.json")
    monkeypatch.setattr("images.remote_distribution.urllib.request.urlopen", fake_urlopen)

    result = ensure_destination_packs(tmp_path, [DestinationRequest("Oslo", "Norway")])

    assert result["ok"] is False
    assert result["code"] == "destination_packs_failed"
    assert any("Checksum mismatch" in error for error in result["errors"])
    assert active_distribution_bank(tmp_path) is None


def test_patch_by_safe_extraction_rejects_traversal(monkeypatch, tmp_path):
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("image_bank_full/../../outside.webp", b"bad")
    malicious = stream.getvalue()
    entry = _manifest_entry("Norway", "Oslo", malicious)
    manifest = _manifest({"Norway/Oslo": entry})

    def fake_urlopen(request, timeout=None):
        return _FakeResponse(manifest if _url(request).endswith("manifest.json") else malicious)

    monkeypatch.setenv("ITINERARY_IMAGE_BANK_MANIFEST_URL", "https://example.test/manifest.json")
    monkeypatch.setattr("images.remote_distribution.urllib.request.urlopen", fake_urlopen)

    result = ensure_destination_packs(tmp_path, [DestinationRequest("Oslo", "Norway")])

    assert result["ok"] is False
    assert any("Unsafe path" in error for error in result["errors"])
    assert not (tmp_path / "outside.webp").exists()
    assert active_distribution_bank(tmp_path) is None


def test_patch_by_connection_adds_missing_pack_without_full_repo_clone(monkeypatch, tmp_path):
    oslo = _pack_bytes("Norway", "Oslo")
    bergen = _pack_bytes("Norway", "Bergen")
    entries = {
        "Norway/Oslo": _manifest_entry("Norway", "Oslo", oslo),
        "Norway/Bergen": _manifest_entry("Norway", "Bergen", bergen),
    }
    manifest = _manifest(entries)
    payloads = {
        "manifest.json": manifest,
        entries["Norway/Oslo"]["asset_name"]: oslo,
        entries["Norway/Bergen"]["asset_name"]: bergen,
    }
    calls: list[str] = []

    def fake_urlopen(request, timeout=None):
        url = _url(request)
        calls.append(url)
        return _FakeResponse(payloads[url.rsplit("/", 1)[-1]])

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_MANIFEST_URL", "https://example.test/manifest.json")
    monkeypatch.setattr("images.remote_distribution.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(image_bank, "_fetch_image_bank_with_git", lambda *_args: (_ for _ in ()).throw(AssertionError("git fallback should not run")))
    monkeypatch.setattr(image_bank, "_fetch_image_bank_with_zip", lambda *_args: (_ for _ in ()).throw(AssertionError("full ZIP fallback should not run")))

    first = image_bank.connect_remote_image_bank_if_missing(
        tmp_path,
        required_destinations=[DestinationRequest("Oslo", "Norway")],
    )
    assert first["required_destinations_ready"] is True
    assert first["setup_status"]["method"] == "destination_packs"

    before = image_bank.image_bank_status(
        tmp_path,
        required_destinations=[DestinationRequest("Bergen", "Norway")],
    )
    assert before["required_destinations_ready"] is False

    second = image_bank.connect_remote_image_bank_if_missing(
        tmp_path,
        required_destinations=[DestinationRequest("Bergen", "Norway")],
    )
    assert second["required_destinations_ready"] is True
    assert second["setup_status"]["method"] == "destination_packs"
    assert any(url.endswith(entries["Norway/Bergen"]["asset_name"]) for url in calls)
    assert not any("archive/refs/heads" in url for url in calls)


def test_patch_by_refreshes_stale_cached_manifest_before_full_repo_fallback(monkeypatch, tmp_path):
    oslo = _pack_bytes("Norway", "Oslo")
    fresh_entry = _manifest_entry("Norway", "Oslo", oslo)
    fresh_manifest = _manifest({"Norway/Oslo": fresh_entry})

    cache_root = tmp_path / image_bank.RUNTIME_IMAGE_BANK_DIR / "distribution"
    cache_root.mkdir(parents=True, exist_ok=True)
    (cache_root / "manifest.json").write_text(json.dumps({
        "schema_version": 1,
        "bank_version": "old-bank",
        "destinations": {
            "Norway/Bergen": _manifest_entry("Norway", "Bergen", _pack_bytes("Norway", "Bergen")),
        },
    }), encoding="utf-8")

    def fake_urlopen(request, timeout=None):
        url = _url(request)
        return _FakeResponse(fresh_manifest if url.endswith("manifest.json") else oslo)

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_BOOTSTRAP", "1")
    monkeypatch.setenv("ITINERARY_IMAGE_BANK_MANIFEST_URL", "https://example.test/manifest.json")
    monkeypatch.setattr("images.remote_distribution.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(image_bank, "_fetch_image_bank_with_git", lambda *_args: (_ for _ in ()).throw(AssertionError("git fallback should not run")))
    monkeypatch.setattr(image_bank, "_fetch_image_bank_with_zip", lambda *_args: (_ for _ in ()).throw(AssertionError("full ZIP fallback should not run")))

    status = image_bank.connect_remote_image_bank_if_missing(
        tmp_path,
        required_destinations=[DestinationRequest("Oslo", "Norway")],
    )

    assert status["required_destinations_ready"] is True
    assert status["setup_status"]["method"] == "destination_packs"
    assert status["setup_status"]["manifest_source"] == "network"
    assert status["setup_status"]["initial_attempt"]["unresolved_destinations"] == ["Norway/Oslo"]
