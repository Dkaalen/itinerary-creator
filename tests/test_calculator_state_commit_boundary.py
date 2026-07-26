from __future__ import annotations

from math import inf
from pathlib import Path

import pytest

from app_modules.calculator_state_commit import (
    CalculatorStateCommitRequest,
    commit_calculator_state,
)
from app_modules.calculator_state_keys import (
    CALCULATOR_ADVANCED_TOGGLE_KEY,
    CALCULATOR_DRAFT_NAMESPACE_KEY,
    CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY,
    CALCULATOR_READY_DOWNLOAD_KEY,
    CALCULATOR_STATE_KEY,
    CURRENCY_RATES_STATE_KEY,
)
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from calculator.state_revision import calculator_state_revision


def _state(name: str, element: str) -> CalculatorState:
    return CalculatorState(
        itinerary_name=name,
        rows=(CalculatorRow(row_id="1", travel_element=element),),
    )


def test_commit_applies_canonical_state_and_related_projections_atomically() -> None:
    previous = _state("Trip", "Old hotel")
    changed = _state("Trip", "New hotel")
    session: dict[str, object] = {
        CALCULATOR_STATE_KEY: previous,
        CALCULATOR_DRAFT_NAMESPACE_KEY: "project:alpha",
        CALCULATOR_READY_DOWNLOAD_KEY: {"filename": "stale.xlsx"},
        "calculator_currency_rate_OLD": 99,
    }

    result = commit_calculator_state(
        session,
        CalculatorStateCommitRequest(
            state=changed,
            source="browser_recovery",
            expected_revision=calculator_state_revision(previous),
            project_identity="project:alpha",
            currency_rates={"nok": 1, "eur": 11.5},
            replace_currency_rates=True,
            show_advanced=True,
            sync_name_input=True,
        ),
    )

    assert result.accepted is True
    assert result.changed is True
    assert result.status == "accepted"
    assert session[CALCULATOR_STATE_KEY] == changed
    assert session[CURRENCY_RATES_STATE_KEY] == {"NOK": 1.0, "EUR": 11.5}
    assert session["calculator_currency_rate_EUR"] == 11.5
    assert "calculator_currency_rate_OLD" not in session
    assert session[CALCULATOR_ADVANCED_TOGGLE_KEY] is True
    assert session[CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY] is True
    assert CALCULATOR_READY_DOWNLOAD_KEY not in session


def test_stale_revision_is_rejected_without_mutation() -> None:
    previous = _state("Trip", "Current")
    session: dict[str, object] = {CALCULATOR_STATE_KEY: previous}

    result = commit_calculator_state(
        session,
        CalculatorStateCommitRequest(
            state=_state("Trip", "Stale"),
            source="draft_recovery",
            expected_revision="older-revision",
        ),
    )

    assert result.accepted is False
    assert result.status == "rejected_stale"
    assert session == {CALCULATOR_STATE_KEY: previous}


def test_project_mismatch_is_rejected_before_revision_guard() -> None:
    previous = _state("Trip", "Current")
    session: dict[str, object] = {
        CALCULATOR_STATE_KEY: previous,
        CALCULATOR_DRAFT_NAMESPACE_KEY: "project:current",
    }

    result = commit_calculator_state(
        session,
        CalculatorStateCommitRequest(
            state=_state("Trip", "Other project"),
            source="browser_recovery",
            expected_revision="also-stale",
            project_identity="project:other",
        ),
    )

    assert result.accepted is False
    assert result.status == "rejected_project"
    assert session[CALCULATOR_STATE_KEY] == previous


def test_invalid_currency_projection_fails_before_any_state_change() -> None:
    previous = _state("Trip", "Current")
    session: dict[str, object] = {
        CALCULATOR_STATE_KEY: previous,
        CURRENCY_RATES_STATE_KEY: {"NOK": 1.0},
        CALCULATOR_READY_DOWNLOAD_KEY: {"filename": "current.xlsx"},
    }
    original = dict(session)

    with pytest.raises(ValueError, match="must be finite"):
        commit_calculator_state(
            session,
            CalculatorStateCommitRequest(
                state=_state("Trip", "Replacement"),
                source="file_restore",
                currency_rates={"EUR": inf},
                replace_currency_rates=True,
            ),
        )

    assert session == original


def test_restore_and_session_application_do_not_import_each_other() -> None:
    restore = Path("app_modules/calculator_restore.py").read_text(encoding="utf-8")
    session = Path("app_modules/calculator_session_state.py").read_text(encoding="utf-8")

    assert "app_modules.calculator_session_state" not in restore
    assert "app_modules.calculator_restore" not in session
    assert "app_modules.calculator_state_commit" in restore
    assert "app_modules.calculator_state_commit" in session
