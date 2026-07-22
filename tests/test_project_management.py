from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app_modules.project_unsaved_state import active_project_has_unsaved_changes
from calculator.calculator_state import add_row, create_calculator_state
from calculator.row_model import CalculatorRow
from calculator.state_serialization import calculator_state_to_dict
from project_storage.project_management import duplicate_project, rename_project


class FakeRepository:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.upserts: list[tuple[str, str, str]] = []
        self.versions: list[dict[str, Any]] = []

    def latest_version(self, itinerary_id: str) -> dict[str, Any] | None:
        return {
            "itinerary_id": itinerary_id,
            "itinerary_type": "agent",
            "payload": self.payload,
        }

    def upsert_itinerary(self, itinerary_id: str, *, name: str, status: str = "draft") -> dict[str, Any]:
        self.upserts.append((itinerary_id, name, status))
        return {"id": itinerary_id, "name": name}

    def next_version_number(self, itinerary_id: str, itinerary_type: str) -> int:
        return 4

    def create_version(self, **kwargs: Any) -> dict[str, Any]:
        self.versions.append(kwargs)
        return kwargs


def _payload() -> dict[str, Any]:
    state = add_row(
        create_calculator_state("Nordic Journey"),
        CalculatorRow(row_id="1", travel_element="Hotel", gross_price_per_unit=100, units=2),
    )
    return {
        "metadata": {
            "project_id": "project-1",
            "itinerary_name": "Nordic Journey",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "status": "draft",
        },
        "output_brand": "agent",
        "calculator_snapshot": calculator_state_to_dict(state),
    }


def test_rename_project_updates_metadata_and_appends_version() -> None:
    repository = FakeRepository(_payload())
    result = rename_project(
        repository,
        project_id="project-1",
        new_name="Renamed Journey",
        clock=lambda: datetime(2026, 7, 13, 12, tzinfo=timezone.utc),
    )

    assert result["project_id"] == "project-1"
    assert result["payload"]["metadata"]["itinerary_name"] == "Renamed Journey"
    assert result["payload"]["calculator_snapshot"]["itinerary_name"] == "Renamed Journey"
    assert repository.upserts == [("project-1", "Renamed Journey", "draft")]
    assert repository.versions[0]["version_number"] == 4
    assert repository.versions[0]["source_type"] == "project_rename"


def test_duplicate_project_gets_new_identity_and_preserves_calculator() -> None:
    repository = FakeRepository(_payload())
    result = duplicate_project(
        repository,
        project_id="project-1",
        new_name="Nordic Journey — Copy",
        id_factory=lambda: "project-2",
        clock=lambda: datetime(2026, 7, 13, 12, tzinfo=timezone.utc),
    )

    assert result["project_id"] == "project-2"
    assert result["payload"]["metadata"]["project_id"] == "project-2"
    assert result["payload"]["metadata"]["itinerary_name"] == "Nordic Journey — Copy"
    assert result["payload"]["calculator_snapshot"]["rows"] == _payload()["calculator_snapshot"]["rows"]
    assert repository.versions[0]["version_number"] == 1
    assert repository.versions[0]["source_type"] == "project_duplicate"


def test_unsaved_change_detection_compares_current_calculator_to_snapshot() -> None:
    payload = _payload()
    saved_state = add_row(
        create_calculator_state("Nordic Journey"),
        CalculatorRow(row_id="1", travel_element="Hotel", gross_price_per_unit=100, units=2),
    )
    session = {
        "active_saved_project": payload,
        "itinerary_name": "Nordic Journey",
        "calculator_state": saved_state,
        "calculator_currency_rates": {},
    }
    assert active_project_has_unsaved_changes(session) is False

    session["calculator_state"] = add_row(
        create_calculator_state("Nordic Journey"),
        CalculatorRow(row_id="1", travel_element="Hotel", gross_price_per_unit=125, units=2),
    )
    assert active_project_has_unsaved_changes(session) is True


def test_unsaved_change_detection_includes_currency_rates() -> None:
    payload = _payload()
    payload["calculator_snapshot"]["currency_rates"] = {"NOK": 1, "EUR": 11.5}
    saved_state = add_row(
        create_calculator_state("Nordic Journey"),
        CalculatorRow(row_id="1", travel_element="Hotel", gross_price_per_unit=100, units=2),
    )
    session = {
        "active_saved_project": payload,
        "itinerary_name": "Nordic Journey",
        "calculator_state": saved_state,
        "calculator_currency_rates": {"NOK": 1, "EUR": 11.6},
    }

    assert active_project_has_unsaved_changes(session) is True


def test_duplicate_project_rejects_source_identity_reuse() -> None:
    repository = FakeRepository(_payload())

    import pytest

    with pytest.raises(ValueError, match="must differ"):
        duplicate_project(
            repository,
            project_id="project-1",
            id_factory=lambda: "project-1",
        )


def test_duplicate_project_handles_missing_metadata_name() -> None:
    payload = _payload()
    payload["metadata"] = []
    repository = FakeRepository(payload)

    result = duplicate_project(
        repository,
        project_id="project-1",
        id_factory=lambda: "project-2",
        clock=lambda: datetime(2026, 7, 13, 12, tzinfo=timezone.utc),
    )

    assert result["name"] == "Untitled itinerary — Copy"
    assert result["payload"]["metadata"]["project_id"] == "project-2"


def test_active_project_rename_updates_all_name_boundaries() -> None:
    from app_modules.calculator_state_keys import (
        CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY,
        CALCULATOR_STATE_KEY,
    )
    from app_modules.project_rename_state import apply_active_project_rename

    calculator_state = add_row(
        create_calculator_state("Old name"),
        CalculatorRow(row_id="1", travel_element="Hotel"),
    )
    session = {
        CALCULATOR_STATE_KEY: calculator_state,
        "itinerary_name": "Old name",
        "itinerary_name_input": "Old name",
        "active_saved_project": _payload(),
    }
    result = {
        "name": "New name",
        "payload": {
            **_payload(),
            "metadata": {**_payload()["metadata"], "itinerary_name": "New name"},
        },
    }

    apply_active_project_rename(session, result)

    assert session["itinerary_name"] == "New name"
    assert session["itinerary_name_input"] == "New name"
    assert session[CALCULATOR_STATE_KEY].itinerary_name == "New name"
    assert session[CALCULATOR_ITINERARY_NAME_SYNC_REQUIRED_KEY] is True
    assert session["active_saved_project"]["metadata"]["itinerary_name"] == "New name"


def test_unsaved_change_detection_normalizes_equivalent_rate_representations() -> None:
    payload = _payload()
    payload["calculator_snapshot"]["currency_rates"] = {"NOK": 1, "EUR": 11.5}
    saved_state = add_row(
        create_calculator_state("Nordic Journey"),
        CalculatorRow(row_id="1", travel_element="Hotel", gross_price_per_unit=100, units=2),
    )
    session = {
        "active_saved_project": payload,
        "itinerary_name": "Nordic Journey",
        "calculator_state": saved_state,
        "calculator_currency_rates": {"NOK": 1.0, "EUR": 11.5000000000000},
    }

    assert active_project_has_unsaved_changes(session) is False


def test_unsaved_change_detection_protects_detached_calculator_rows() -> None:
    calculator_state = add_row(
        create_calculator_state("Local workbook"),
        CalculatorRow(row_id="1", travel_element="Oslo hotel", gross_price_per_unit=120, units=1),
    )
    session = {
        "calculator_state": calculator_state,
        "calculator_currency_rates": {"NOK": 1, "EUR": 11.5},
    }

    assert active_project_has_unsaved_changes(session) is True


def test_unsaved_change_detection_ignores_empty_calculator_starter_rows() -> None:
    calculator_state = add_row(
        create_calculator_state(""),
        CalculatorRow(row_id="1"),
    )
    session = {
        "calculator_state": calculator_state,
        "calculator_currency_rates": {"NOK": 1, "EUR": 11.5},
    }

    assert active_project_has_unsaved_changes(session) is False
