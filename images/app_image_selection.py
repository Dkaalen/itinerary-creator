"""App-facing day image helpers."""

from images.image_bank import (
    APP_ROOT,
    clean_space,
    esc,
    ensure_runtime_image_bank as _ensure_runtime_image_bank,
    get_image_bank_path as _get_image_bank_path,
    get_image_bank_paths as _get_image_bank_paths,
    get_image_bank_scan_paths as _get_image_bank_scan_paths,
    image_bank_status as _image_bank_status,
    infer_country_for_city as _infer_country_for_city,
    normalize_path_key,
    slugify_filename,
)
from images.image_overrides import (
    CROP_FOCUS_LABELS,
    CROP_FOCUS_OBJECT_POSITIONS,
    CROP_FOCUS_OPTIONS,
    get_day_image_choice,
    get_day_image_crop_focus,
    get_day_image_overrides,
    normalize_crop_focus,
)
from images.image_preview import (
    get_image_preview_for_path,
    image_to_data_uri,
    image_to_option_preview_data_uri,
    image_to_preview_data_uri,
)
from images.day_image_selection import day_image_match_from_path
from images.day_image_selection import select_day_images_with_overrides as _select_day_images_with_overrides
from images.replacement_options import (
    list_replacement_image_options as _list_replacement_image_options,
    list_replacement_image_options_for_rows as _list_replacement_image_options_for_rows,
)
from images.image_uploads import (
    save_uploaded_day_image as _save_uploaded_day_image,
    save_data_uri_day_image as _save_data_uri_day_image,
)
from images.day_image_ui import render_day_image_slot as _render_day_image_slot
from images.image_match_audit import audit_day_image_matches as _audit_day_image_matches




def ensure_runtime_image_bank():
    return _ensure_runtime_image_bank(APP_ROOT)


def image_bank_status():
    return _image_bank_status(APP_ROOT)

def get_image_bank_paths():
    return _get_image_bank_paths(APP_ROOT)


def get_image_bank_path():
    return _get_image_bank_path(APP_ROOT)


def get_image_bank_scan_paths():
    return _get_image_bank_scan_paths(APP_ROOT)


def infer_country_for_city(city):
    return _infer_country_for_city(city, APP_ROOT)


def select_day_images_with_overrides(grouped_days, output_edits=None):
    return _select_day_images_with_overrides(grouped_days, output_edits, app_root=APP_ROOT, image_bank_scan_paths=get_image_bank_scan_paths())


def list_replacement_image_options(city):
    return _list_replacement_image_options(city, image_bank_scan_paths=get_image_bank_scan_paths())


def list_replacement_image_options_for_rows(day, rows, limit=30):
    return _list_replacement_image_options_for_rows(day, rows, limit=limit, image_bank_scan_paths=get_image_bank_scan_paths())


def save_uploaded_day_image(uploaded_file, city, season, label=""):
    return _save_uploaded_day_image(uploaded_file, city, season, label, image_bank_path=get_image_bank_path(), infer_country_for_city=infer_country_for_city)


def save_data_uri_day_image(data_uri, filename, city, season="Summer", label=""):
    return _save_data_uri_day_image(data_uri, filename, city, season, label, image_bank_path=get_image_bank_path(), infer_country_for_city=infer_country_for_city)


def render_day_image_slot(day, rows, match=None, output_edits=None):
    return _render_day_image_slot(day, rows, match=match, output_edits=output_edits, image_bank_scan_paths=get_image_bank_scan_paths())


def audit_day_image_matches(grouped_days, image_matches, output_edits=None):
    return _audit_day_image_matches(
        grouped_days,
        image_matches,
        output_edits=output_edits,
        image_bank_scan_paths=get_image_bank_scan_paths(),
    )
