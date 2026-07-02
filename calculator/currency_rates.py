"""Default calculator exchange rates to NOK."""

from __future__ import annotations

# Conservative editable defaults used when live currency rates are not configured.
# Keep this list within the template lookup range Curr!$B$2:$C$13.
DEFAULT_CURRENCY_RATES: dict[str, float] = {
    "NOK": 1.0,
    "EUR": 11.0,
    "USD": 10.0,
    "GBP": 13.0,
    "DKK": 1.5,
    "SEK": 1.0,
    "ISK": 0.08,
    "CHF": 12.0,
    "CAD": 7.5,
    "AUD": 7.0,
    "PLN": 2.5,
    "JPY": 0.07,
}


def normalized_currency_code(value: object, *, default: str = "EUR") -> str:
    """Return an uppercase currency code, falling back to the calculator default."""

    code = str(value or "").strip().upper()
    return code or default
