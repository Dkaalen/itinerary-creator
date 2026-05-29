"""Day-image override and crop-focus helpers."""

CROP_FOCUS_OPTIONS = {
    "Sky / upper focus": "top",
    "Center focus": "center",
    "Lower focus": "bottom",
}

CROP_FOCUS_LABELS = {value: label for label, value in CROP_FOCUS_OPTIONS.items()}

CROP_FOCUS_OBJECT_POSITIONS = {
    "top": "center 22%",
    "center": "center center",
    "bottom": "center 78%",
}

def get_day_image_overrides(output_edits=None):
    return (output_edits or {}).setdefault("day_images", {})

def normalize_crop_focus(value):
    value = str(value or "").strip().lower()
    if value in {"top", "upper", "sky", "aurora"}:
        return "top"
    if value in {"bottom", "lower"}:
        return "bottom"
    if value in {"center", "centre", "middle"}:
        return "center"
    return "top"

def get_day_image_choice(output_edits, day):
    day_images = get_day_image_overrides(output_edits)
    choice = day_images.setdefault(day, {"mode": "auto", "path": "", "crop_focus": "top"})
    choice.setdefault("mode", "auto")
    choice.setdefault("path", "")
    choice["crop_focus"] = normalize_crop_focus(choice.get("crop_focus", "top"))
    return choice

def get_day_image_crop_focus(output_edits, day):
    return normalize_crop_focus(get_day_image_choice(output_edits, day).get("crop_focus", "top"))

