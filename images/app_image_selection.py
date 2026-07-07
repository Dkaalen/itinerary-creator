"""App-facing day image helpers."""

from images.image_bank import (
    APP_ROOT,
    clean_space,
    destination_requests_from_rows,
    esc,
    normalize_path_key,
    slugify_filename,
)
from images import app_image_bank as _app_image_bank
from images.image_overrides import (
    CROP_FOCUS_LABELS,
    CROP_FOCUS_OBJECT_POSITIONS,
    CROP_FOCUS_OPTIONS,
    get_day_image_choice,
    get_day_image_crop_focus,
    get_day_image_overrides,
    read_day_image_choice,
    read_day_image_crop_focus,
    normalize_crop_focus,
)
from images.image_preview import (
    get_image_preview_for_path,
    image_to_data_uri,
    image_to_option_preview_data_uri,
    image_to_preview_data_uri,
)
from images.day_image_selection import day_image_match_from_path, normalize_day_image_match, normalize_day_image_matches
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



def ensure_runtime_image_bank(required_destinations=None):
    return _app_image_bank.ensure_runtime_image_bank(required_destinations, root=APP_ROOT)


def ensure_runtime_image_bank_status(required_destinations=None):
    return _app_image_bank.ensure_runtime_image_bank_status(required_destinations, root=APP_ROOT)


def connect_remote_image_bank_if_missing(required_destinations=None):
    return _app_image_bank.connect_remote_image_bank_if_missing(required_destinations, root=APP_ROOT)


def image_bank_status(required_destinations=None):
    return _app_image_bank.image_bank_status(required_destinations, root=APP_ROOT)


def image_bank_storage_signature():
    return _app_image_bank.image_bank_storage_signature(root=APP_ROOT)


def prefetch_image_bank_for_rows(rows_or_grouped_days):
    return _app_image_bank.prefetch_image_bank_for_rows(rows_or_grouped_days, root=APP_ROOT)


def get_image_bank_paths():
    return _app_image_bank.get_image_bank_paths(root=APP_ROOT)


def get_image_bank_path():
    return _app_image_bank.get_image_bank_path(root=APP_ROOT)


def get_image_bank_scan_paths():
    return _app_image_bank.get_image_bank_scan_paths(root=APP_ROOT)


def infer_country_for_city(city):
    return _app_image_bank.infer_country_for_city(city, root=APP_ROOT)


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
