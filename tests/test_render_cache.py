from ui.render_cache import make_render_signature


def test_render_signature_is_stable_for_same_content():
    rows = [{"day": "Day 1", "city": "Oslo", "title": "Arrival"}]
    edits = {"trip_title": "Norway Escape", "days": {"Day 1": {"title": "Welcome"}}}

    first = make_render_signature(rows, edits)
    second = make_render_signature(list(rows), dict(edits))

    assert first == second


def test_render_signature_changes_when_preview_content_changes():
    rows = [{"day": "Day 1", "city": "Oslo", "title": "Arrival"}]
    original = {"trip_title": "Norway Escape", "days": {"Day 1": {"title": "Welcome"}}}
    edited = {"trip_title": "Edited Norway Escape", "days": {"Day 1": {"title": "Welcome"}}}

    assert make_render_signature(rows, original) != make_render_signature(rows, edited)
