from __future__ import annotations

from visual_editor_component import editor_payload_images


def _rows():
    return [
        {
            "row_id": "row-1",
            "day": "Day 1",
            "type": "Activity",
            "city": "Oslo",
            "title": "Oslo City Walk",
            "details": "Guided walk through the city centre.",
        }
    ]


def _patch_fast_image_helpers(monkeypatch, calls, *, bank_signature="bank:v1"):
    monkeypatch.setattr(editor_payload_images, "_image_bank_signature", lambda *, pictures_added: bank_signature)

    def fake_select(grouped_days, output_edits):
        calls["select"] = calls.get("select", 0) + 1
        return {day: {"path": f"/image-bank/{day.replace(' ', '-').lower()}.jpg"} for day in grouped_days}

    def fake_audit(grouped_days, image_matches, output_edits):
        calls["audit"] = calls.get("audit", 0) + 1
        return ()

    def fake_options(day, rows, limit):
        calls["options"] = calls.get("options", 0) + 1
        return [{"path": f"/image-bank/{day.replace(' ', '-').lower()}-option.jpg", "name": "Replacement"}]

    def fake_preview(path, option=False):
        calls["preview"] = calls.get("preview", 0) + 1
        return f"preview:{path}:{option}"

    def fake_cover(parsed_rows, output_edits, key, *, pictures_added):
        calls[f"cover:{key}"] = calls.get(f"cover:{key}", 0) + 1
        return {"mode": "auto", "path": "", "data_uri": "", "crop_focus": "top", "options": []}

    monkeypatch.setattr(editor_payload_images, "select_day_images_with_overrides", fake_select)
    monkeypatch.setattr(editor_payload_images, "audit_day_image_matches", fake_audit)
    monkeypatch.setattr(editor_payload_images, "list_replacement_image_options_for_rows", fake_options)
    monkeypatch.setattr(editor_payload_images, "get_image_preview_for_path", fake_preview)
    monkeypatch.setattr(editor_payload_images, "_editor_cover_image_payload", fake_cover)


def test_visual_editor_image_payload_bundle_reuses_heavy_image_work(monkeypatch):
    editor_payload_images.clear_editor_image_payload_cache()
    calls = {}
    _patch_fast_image_helpers(monkeypatch, calls)
    rows = _rows()
    grouped = {"Day 1": rows}
    edits = {"pictures_added": True, "day_images": {}}

    first = editor_payload_images.build_editor_image_payload_bundle(rows, grouped, edits, pictures_added=True)
    second = editor_payload_images.build_editor_image_payload_bundle(rows, grouped, dict(edits), pictures_added=True)

    assert first == second
    assert calls["select"] == 1
    assert calls["audit"] == 1
    assert calls["options"] == 1
    assert calls["preview"] == 2
    assert calls["cover:cover_image"] == 1
    assert calls["cover:summary_image"] == 1


def test_visual_editor_image_payload_cache_returns_isolated_copies(monkeypatch):
    editor_payload_images.clear_editor_image_payload_cache()
    calls = {}
    _patch_fast_image_helpers(monkeypatch, calls)
    rows = _rows()
    grouped = {"Day 1": rows}
    edits = {"pictures_added": True, "day_images": {}}

    first = editor_payload_images.build_editor_image_payload_bundle(rows, grouped, edits, pictures_added=True)
    first["day_images"]["Day 1"]["path"] = "/mutated/in/test.jpg"
    second = editor_payload_images.build_editor_image_payload_bundle(rows, grouped, edits, pictures_added=True)

    assert second["day_images"]["Day 1"]["path"] == "/image-bank/day-1.jpg"
    assert calls["select"] == 1


def test_visual_editor_image_payload_cache_invalidates_for_image_edits(monkeypatch):
    editor_payload_images.clear_editor_image_payload_cache()
    calls = {}
    _patch_fast_image_helpers(monkeypatch, calls)
    rows = _rows()
    grouped = {"Day 1": rows}

    first = editor_payload_images.build_editor_image_payload_bundle(
        rows,
        grouped,
        {"pictures_added": True, "day_images": {"Day 1": {"mode": "auto", "crop_focus": "top"}}},
        pictures_added=True,
    )
    second = editor_payload_images.build_editor_image_payload_bundle(
        rows,
        grouped,
        {"pictures_added": True, "day_images": {"Day 1": {"mode": "auto", "crop_focus": "center"}}},
        pictures_added=True,
    )

    assert first["day_images"]["Day 1"]["crop_focus"] == "top"
    assert second["day_images"]["Day 1"]["crop_focus"] == "center"
    assert calls["select"] == 2
    assert calls["options"] == 2


def test_visual_editor_image_payload_build_does_not_seed_output_edits(monkeypatch):
    editor_payload_images.clear_editor_image_payload_cache()
    calls = {}
    _patch_fast_image_helpers(monkeypatch, calls)
    rows = _rows()
    grouped = {"Day 1": rows}
    edits = {"pictures_added": True}

    payload = editor_payload_images.build_editor_image_payload_bundle(rows, grouped, edits, pictures_added=True)

    assert payload["day_images"]["Day 1"]["mode"] == "auto"
    assert "day_images" not in edits


def test_visual_editor_image_payload_cache_invalidates_for_image_bank_changes(monkeypatch):
    editor_payload_images.clear_editor_image_payload_cache()
    calls = {}
    bank = {"value": "bank:v1"}
    _patch_fast_image_helpers(monkeypatch, calls)
    monkeypatch.setattr(editor_payload_images, "_image_bank_signature", lambda *, pictures_added: bank["value"])
    rows = _rows()
    grouped = {"Day 1": rows}
    edits = {"pictures_added": True, "day_images": {}}

    editor_payload_images.build_editor_image_payload_bundle(rows, grouped, edits, pictures_added=True)
    bank["value"] = "bank:v2"
    editor_payload_images.build_editor_image_payload_bundle(rows, grouped, edits, pictures_added=True)

    assert calls["select"] == 2
    assert calls["options"] == 2
