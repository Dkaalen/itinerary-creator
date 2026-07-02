"""Render editable calculator currency-rate controls."""

from __future__ import annotations

from collections.abc import MutableMapping

import streamlit as st

from calculator.currency_rates import DEFAULT_CURRENCY_RATES, normalize_currency_rates

CURRENCY_RATES_STATE_KEY = "calculator_currency_rates"


def currency_rates_from_session(session_state: MutableMapping[str, object]) -> dict[str, float]:
    """Return the active calculator currency rates from Streamlit session state."""

    rates = normalize_currency_rates(session_state.get(CURRENCY_RATES_STATE_KEY))
    session_state[CURRENCY_RATES_STATE_KEY] = rates
    return rates


def render_currency_rate_editor(session_state: MutableMapping[str, object]) -> dict[str, float]:
    """Render compact editable NOK exchange-rate defaults and return active rates."""

    rates = currency_rates_from_session(session_state)
    with st.expander("Currency rates", expanded=False):
        st.caption("Base currency is NOK. These rates update the calculator and the Excel export.")
        columns = st.columns(6)
        updated: dict[str, float] = {}
        for index, (code, default_rate) in enumerate(DEFAULT_CURRENCY_RATES.items()):
            with columns[index % len(columns)]:
                updated[code] = float(
                    st.number_input(
                        code,
                        value=float(rates.get(code, default_rate)),
                        min_value=0.0,
                        step=_rate_step(default_rate),
                        format="%.4f",
                        key=f"calculator_currency_rate_{code}",
                    )
                )
        if st.button("Reset currency rates", use_container_width=True):
            session_state[CURRENCY_RATES_STATE_KEY] = dict(DEFAULT_CURRENCY_RATES)
            st.rerun()
        rates = normalize_currency_rates(updated)
        session_state[CURRENCY_RATES_STATE_KEY] = rates
    return rates


def _rate_step(default_rate: float) -> float:
    return 0.01 if default_rate < 1 else 0.1
