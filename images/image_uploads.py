"""Upload helpers for adding day images to the local image bank."""

from __future__ import annotations

import base64
import binascii

import diagnostics
from pathlib import Path

from text_polish import polish_title
from images.image_bank import slugify_filename


def save_uploaded_day_image(uploaded_file, city, season, label="", *, image_bank_path, infer_country_for_city):
    if not uploaded_file:
        return ""
    city_name = polish_title(city) or "Destination"
    country = infer_country_for_city(city_name)
    season_name = season if season in {"Summer", "Winter"} else "Summer"
    stem_bits = [slugify_filename(city_name), season_name, slugify_filename(label or Path(uploaded_file.name).stem)]
    suffix = Path(uploaded_file.name).suffix.lower() or ".jpg"
    target_dir = image_bank_path / slugify_filename(country) / slugify_filename(city_name)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / ("_".join([bit for bit in stem_bits if bit]) + suffix)

    counter = 2
    while target_path.exists():
        target_path = target_dir / ("_".join([bit for bit in stem_bits if bit]) + f"_{counter}" + suffix)
        counter += 1

    target_path.write_bytes(uploaded_file.getbuffer())
    return str(target_path)


def save_data_uri_day_image(data_uri, filename, city, season='Summer', label='', *, image_bank_path, infer_country_for_city):
    """Save a visual-editor uploaded data URI into the local image bank."""
    if not data_uri or not str(data_uri).startswith('data:'):
        return ''
    try:
        header, encoded = str(data_uri).split(',', 1)
        raw = base64.b64decode(encoded)
    except (ValueError, binascii.Error) as error:
        diagnostics.warn_exception("image_upload", "Could not decode uploaded visual-editor image data.", error, filename, source="images.image_uploads")
        return ''

    class _UploadedBytes:
        def __init__(self, name, data):
            self.name = name or 'uploaded_image.jpg'
            self._data = data
        def getbuffer(self):
            return self._data

    return save_uploaded_day_image(_UploadedBytes(filename, raw), city, season, label, image_bank_path=image_bank_path, infer_country_for_city=infer_country_for_city)


