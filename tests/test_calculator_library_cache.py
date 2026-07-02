from __future__ import annotations

from app_modules.calculator_library_cache import clear_cached_local_library, read_cached_local_library
from calculator.library_model import LocalLibraryRow
from calculator.library_store import LocalLibraryReadResult


def test_cached_local_library_reuses_fresh_result() -> None:
    calls = 0

    def reader() -> LocalLibraryReadResult:
        nonlocal calls
        calls += 1
        return LocalLibraryReadResult(rows=(LocalLibraryRow(library_id=f"row_{calls}"),), source="test", read_only=False)

    session_state: dict[str, object] = {}

    first = read_cached_local_library(session_state, reader=reader)
    second = read_cached_local_library(session_state, reader=reader)

    assert calls == 1
    assert first is second
    assert second.rows[0].library_id == "row_1"


def test_cached_local_library_can_be_cleared() -> None:
    session_state: dict[str, object] = {}
    result = LocalLibraryReadResult(rows=(), source="test", read_only=False)

    read_cached_local_library(session_state, reader=lambda: result)
    clear_cached_local_library(session_state)

    assert session_state == {}


def test_cached_local_library_force_refresh_reads_again() -> None:
    calls = 0

    def reader() -> LocalLibraryReadResult:
        nonlocal calls
        calls += 1
        return LocalLibraryReadResult(rows=(LocalLibraryRow(library_id=f"row_{calls}"),), source="test", read_only=False)

    session_state: dict[str, object] = {}

    first = read_cached_local_library(session_state, reader=reader)
    second = read_cached_local_library(session_state, force_refresh=True, reader=reader)

    assert calls == 2
    assert first.rows[0].library_id == "row_1"
    assert second.rows[0].library_id == "row_2"
