from app_modules.render_context_cache import (
    get_cached_render_context,
    store_render_context,
    clear_render_context_cache,
)
from app_modules.itinerary_render_context import build_itinerary_render_context


def _context():
    rows = [{"day": "Day 1", "type": "Activity", "effective_type": "Activity", "city": "Oslo", "title": "Walk"}]
    return build_itinerary_render_context(rows, {"Day 1": rows}, {"days": {}})


def test_render_context_cache_returns_only_matching_signature():
    state = {}
    context = _context()

    store_render_context(state, signature="sig-1", context=context)

    assert get_cached_render_context(state, signature="sig-1") is context
    assert get_cached_render_context(state, signature="sig-2") is None


def test_render_context_cache_can_be_cleared():
    state = {}
    store_render_context(state, signature="sig-1", context=_context())

    clear_render_context_cache(state)

    assert get_cached_render_context(state, signature="sig-1") is None
