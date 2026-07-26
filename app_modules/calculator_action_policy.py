"""Backend validation and state-commit policy for Calculator browser actions."""

from __future__ import annotations

from app_modules.calculator_component_result import CalculatorGridResult
from calculator.validation import CalculatorValidationScope, validate_calculator_state


def calculator_action_validation_issues(
    result: CalculatorGridResult,
    currency_rates: dict[str, float] | None = None,
):
    """Validate one browser action at the backend trust boundary."""

    scope = {
        "download": CalculatorValidationScope.EXPORT,
        "generate_agent": CalculatorValidationScope.GENERATION,
        "generate_customer": CalculatorValidationScope.GENERATION,
        "sync": CalculatorValidationScope.PERSISTENCE,
    }.get(result.action, CalculatorValidationScope.DRAFT_SAFE)
    return validate_calculator_state(result.state, currency_rates, scope=scope)


def calculator_action_updates_session_state(
    result: CalculatorGridResult,
    currency_rates: dict[str, float] | None = None,
) -> bool:
    """Return whether browser rows may become the backend Calculator authority."""

    if result.action == "open_excel":
        return False
    if result.action in {"close", "open_library", "generate_agent", "generate_customer"}:
        backend_has_display_errors = bool(
            validate_calculator_state(
                result.state,
                currency_rates,
                scope=CalculatorValidationScope.EXPORT,
            )
        )
        if result.client_has_validation_errors or backend_has_display_errors:
            return False
    return True


__all__ = [
    "calculator_action_updates_session_state",
    "calculator_action_validation_issues",
]
