from __future__ import annotations

from pathlib import Path

from PIL import Image

from images.matcher import select_day_image


def _save_jpg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (48, 32), (80, 120, 140)).save(path, format="JPEG")


def _southern_city_rows(city: str, date: str = "18.09.2026") -> list[dict]:
    return [
        {
            "day": "Day 1",
            "date": date,
            "type": "Activity",
            "effective_type": "Activity",
            "city": city,
            "title": f"{city} harbour and city walk",
            "details": "Coastal waterfront, city streets and scenic views.",
        }
    ]


def test_southern_coastal_cities_use_non_winter_images_in_september(tmp_path):
    bank = tmp_path / "image_bank"
    cities = ("Bergen", "Kristiansand", "Stavanger")
    for city in cities:
        city_dir = bank / "Norway" / city
        _save_jpg(city_dir / f"{city}_Autumn_Winter_Snow_Harbour.jpg")
        _save_jpg(city_dir / f"{city}_Summer_Coastal_Harbour_Waterfront.jpg")

    for city in cities:
        match = select_day_image("Day 1", _southern_city_rows(city), bank)

        assert match is not None
        filename = Path(match["path"]).name.lower()
        assert "summer" in filename
        assert "snow" not in filename
        assert "winter" not in filename


def test_southern_coastal_winter_images_are_allowed_from_november_to_march(tmp_path):
    bank = tmp_path / "image_bank"
    city_dir = bank / "Norway" / "Bergen"
    _save_jpg(city_dir / "Bergen_Winter_Snow_Harbour.jpg")
    _save_jpg(city_dir / "Bergen_Summer_Coastal_Harbour_Waterfront.jpg")

    match = select_day_image("Day 1", _southern_city_rows("Bergen", "15.12.2026"), bank)

    assert match is not None
    assert "Winter" in Path(match["path"]).name


def test_southern_coastal_autumn_season_availability_ignores_blocked_snow_images(tmp_path):
    bank = tmp_path / "image_bank"
    city_dir = bank / "Norway" / "Kristiansand"
    _save_jpg(city_dir / "Kristiansand_Autumn_Winter_Snow_City.jpg")
    _save_jpg(city_dir / "Kristiansand_Summer_Coastal_City.jpg")

    match = select_day_image("Day 1", _southern_city_rows("Kristiansand", "01.10.2026"), bank)

    assert match is not None
    assert Path(match["path"]).name == "Kristiansand_Summer_Coastal_City.jpg"
