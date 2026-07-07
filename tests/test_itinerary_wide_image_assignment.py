from __future__ import annotations

from pathlib import Path

from PIL import Image

from images.matcher_selection import select_day_images


def _write_webp(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 20), (20, 80, 120)).save(path, format="WEBP")


def test_global_image_assignment_keeps_specific_image_for_best_later_day(tmp_path: Path) -> None:
    bank = tmp_path / "image_bank_full"
    reykjavik = bank / "Iceland" / "Reykjavik"
    _write_webp(reykjavik / "Reykjavik_Golden_Circle_Geysir_Waterfall_Summer_01.webp")
    _write_webp(reykjavik / "Reykjavik_City_Walking_Summer_01.webp")

    matches = select_day_images(
        {
            "Day 1": [
                {"day": "Day 1", "date": "01/07/2026", "city": "Reykjavik", "title": "Arrival in Reykjavik", "details": "Evening at leisure."}
            ],
            "Day 2": [
                {"day": "Day 2", "date": "02/07/2026", "city": "Reykjavik", "title": "Golden Circle", "details": "Visit Geysir and waterfalls on the Golden Circle route."}
            ],
        },
        bank,
    )

    assert matches["Day 2"]
    assert "Golden_Circle" in Path(matches["Day 2"]["path"]).name
    assert matches["Day 1"]
    assert "Golden_Circle" not in Path(matches["Day 1"]["path"]).name
