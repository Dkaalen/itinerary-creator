"""Small helpers for the staged text-first / picture-review workflow."""

PICTURES_ADDED_KEY = "pictures_added"


def pictures_are_added(output_edits):
    """Return whether the editable project has entered picture-review mode."""
    return bool((output_edits or {}).get(PICTURES_ADDED_KEY))


def set_pictures_added(output_edits, enabled=True):
    """Persist picture-review mode on the editable project state."""
    if output_edits is not None:
        output_edits[PICTURES_ADDED_KEY] = bool(enabled)
    return output_edits
