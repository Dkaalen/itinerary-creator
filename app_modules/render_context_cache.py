"""Session-local preview render-context cache helpers.

The preview, visual editor and PDF exporter should agree on the same generated
render contract.  Streamlit session state is a safe cache boundary: it avoids
cross-user/global stale data while letting PDF export reuse the context already
built for the current preview signature.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping

from app_modules.itinerary_render_context import ItineraryRenderContext

RENDER_CONTEXT_STATE_KEY = "_preview_render_context"
RENDER_CONTEXT_SIGNATURE_STATE_KEY = "_preview_render_context_signature"


def store_render_context(
    state: MutableMapping[str, Any],
    *,
    signature: str | None,
    context: ItineraryRenderContext | None,
) -> None:
    """Store the render context that produced the visible preview."""

    if not signature or context is None:
        clear_render_context_cache(state)
        return
    state[RENDER_CONTEXT_STATE_KEY] = context
    state[RENDER_CONTEXT_SIGNATURE_STATE_KEY] = str(signature)


def get_cached_render_context(
    state: Mapping[str, Any],
    *,
    signature: str | None,
) -> ItineraryRenderContext | None:
    """Return the cached preview context only when the signature matches."""

    if not signature:
        return None
    if str(state.get(RENDER_CONTEXT_SIGNATURE_STATE_KEY) or "") != str(signature):
        return None
    context = state.get(RENDER_CONTEXT_STATE_KEY)
    return context if isinstance(context, ItineraryRenderContext) else None


def clear_render_context_cache(state: MutableMapping[str, Any]) -> None:
    """Drop cached preview render context metadata."""

    state.pop(RENDER_CONTEXT_STATE_KEY, None)
    state.pop(RENDER_CONTEXT_SIGNATURE_STATE_KEY, None)
