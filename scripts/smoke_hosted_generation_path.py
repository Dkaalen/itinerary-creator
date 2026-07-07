"""Smoke-test the hosted generation path without opening Streamlit UI.

The hosted app path is Streamlit-driven, but the crash-prone work happens in the
same Python pipeline exercised here: calculator/raw input -> generation action ->
preview render context -> HTML render document for both client and agent output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _install_streamlit_import_shim() -> None:
    """Allow the smoke script to run in test shells without Streamlit installed."""

    try:
        import streamlit  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    import types

    class _NoOpContext:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class _StreamlitShim(types.SimpleNamespace):
        def __getattr__(self, _name):
            def _noop(*_args, **_kwargs):
                return None
            return _noop

        def expander(self, *_args, **_kwargs):
            return _NoOpContext()

    sys.modules["streamlit"] = _StreamlitShim(session_state={}, secrets={})


_install_streamlit_import_shim()

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app_modules.generation_action as generation_action
from app_modules.calculator_generation_action import generate_itinerary_from_calculator
from app_modules.render_context_cache import RENDER_CONTEXT_STATE_KEY
from calculator.calculator_state import CalculatorState
from calculator.row_model import CalculatorRow
from itinerary_generation.day_brain_report import build_day_brain_report

# Keep this smoke deterministic and offline. The image prefetcher is separately
# covered by image-bank tests and should not decide whether the app generation
# pipeline itself is healthy.
generation_action.prefetch_image_bank_for_rows = lambda _rows: False


def _calculator_state() -> CalculatorState:
    return CalculatorState(
        itinerary_name="Day Brain Hosted Smoke",
        rows=(
            CalculatorRow(row_id="1", day="Day 1", type="Arrival", travel_element="Arrival in Helsinki"),
            CalculatorRow(row_id="2", day="Day 1", type="Transfer", travel_element="Private transfer from Helsinki Airport to Helsinki Central Station"),
            CalculatorRow(row_id="3", day="Day 1", type="Train", travel_element="Santa Claus Express Helsinki to Rovaniemi - overnight train"),
            CalculatorRow(row_id="4", day="Day 2", type="Transfer", travel_element="Private transfer from Rovaniemi Station to your accommodation"),
            CalculatorRow(row_id="5", day="Day 2", type="Hotel", travel_element="Hotel stay in Rovaniemi"),
            CalculatorRow(row_id="6", day="Day 3", type="Leisure", travel_element="A day at leisure in Rovaniemi"),
        ),
    )


def run_generation_smoke(*, output_brand: str) -> dict[str, Any]:
    """Run the same generation path used by the calculator button."""

    state: dict[str, Any] = {
        "active_app_page": "calculator",
        "presentation_language": "English",
        "tone_preset": "Premium concise",
    }
    result = generate_itinerary_from_calculator(state, _calculator_state(), output_brand=output_brand)
    render_context = state.get(RENDER_CONTEXT_STATE_KEY)
    parsed_rows = state.get("parsed_rows") or []
    grouped_days = render_context.grouped_days if render_context else {}
    day_report = build_day_brain_report(grouped_days)
    render_days = list(getattr(getattr(render_context, "render_document", None), "days", []) or [])
    warnings = list(getattr(getattr(render_context, "render_document", None), "warnings", []) or [])
    return {
        "output_brand": output_brand,
        "ok": bool(result.ok),
        "stage": result.stage,
        "message": result.message,
        "parsed_row_count": len(parsed_rows),
        "html_created": bool(state.get("itinerary_html")),
        "render_context_cached": render_context is not None,
        "render_day_count": len(render_days),
        "render_intros": [day.intro for day in render_days],
        "warning_count": len(warnings),
        "warnings": warnings,
        "day_brain_issue_count": day_report["issue_count"],
        "day_brain_intents": [day["intent"] for day in day_report["days"]],
    }


def build_smoke_report() -> list[dict[str, Any]]:
    return [
        run_generation_smoke(output_brand="agent"),
        run_generation_smoke(output_brand="booknordics_customer"),
    ]


def main() -> int:
    report = build_smoke_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    failures = [item for item in report if not item["ok"] or not item["html_created"] or not item["render_context_cached"] or item["day_brain_issue_count"]]
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
