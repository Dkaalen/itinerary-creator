from __future__ import annotations

from io import BytesIO

from app_modules.calculator_backup_action import prepare_calculator_backup_download, read_calculator_backup
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow


class UploadedBytes(BytesIO):
    def getvalue(self) -> bytes:  # type: ignore[override]
        return super().getvalue()


def test_prepare_calculator_backup_download_returns_json_payload() -> None:
    state = CalculatorState(
        itinerary_name='Tromsø: "Winter" / 2026',
        rows=(CalculatorRow(row_id="1", type="Activity", travel_element="Aurora chase"),),
    )

    backup = prepare_calculator_backup_download(state)

    assert backup.filename == "Tromsø Winter 2026 - Calculator Backup.json"
    assert backup.content.startswith(b"{")
    assert read_calculator_backup(UploadedBytes(backup.content)) == state
