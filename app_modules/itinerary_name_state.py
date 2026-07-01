"""Helpers for the optional itinerary name workflow state."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping

ITINERARY_NAME_KEY = "itinerary_name"
ITINERARY_NAME_INPUT_KEY = "itinerary_name_input"


def clean_itinerary_name(value: object) -> str:
    """Return a compact user-facing itinerary name."""

    return " ".join(str(value or "").split())


def itinerary_name_from_state(state: Mapping[str, object]) -> str:
    """Resolve the current itinerary name from canonical state or input state."""

    return clean_itinerary_name(state.get(ITINERARY_NAME_KEY) or state.get(ITINERARY_NAME_INPUT_KEY) or "")


def sync_itinerary_name_from_input(state: MutableMapping[str, object]) -> str:
    """Persist the text-input itinerary name into the canonical state key."""

    name = clean_itinerary_name(state.get(ITINERARY_NAME_INPUT_KEY) or state.get(ITINERARY_NAME_KEY) or "")
    state[ITINERARY_NAME_KEY] = name
    return name


def seed_itinerary_name_input(state: MutableMapping[str, object]) -> None:
    """Initialize the Streamlit text-input key from canonical project state."""

    if ITINERARY_NAME_INPUT_KEY not in state:
        state[ITINERARY_NAME_INPUT_KEY] = clean_itinerary_name(state.get(ITINERARY_NAME_KEY) or "")
