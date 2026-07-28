# Batch 1 — Workflow reliability, persistence, UX, and architecture hardening

This batch moves the app toward deterministic workflow transitions instead of page-local pending flags.

## Workflow transaction model

Hard browser/server transitions now share `app_modules/workflow_transactions.py`:

- `add_pictures`: saves the visible editor model before destination image matching.
- `create_pdf`: saves visible document and picture edits before PDF creation.

The model exposes four states: `idle`, `waiting_for_browser`, `ready`, and `timed_out`. Pages still render their own UI, but they now consume the same transaction contract and copy helpers.

## Calculator persistence model

Saved project files now include a compact `calculator_snapshot` payload. It stores:

- calculator itinerary name
- calculator rows
- active currency rates

A bounded IndexedDB store remains a short-term recovery layer for the custom grid, while project files and Streamlit session state are the durable source of truth. Only one-time migration metadata and unrelated framework settings may remain in localStorage.

## Image-bank readiness model

Normal UI copy now flows through `app_modules/image_bank_readiness.py`. Destination images remain preferred. Fallback images are described as a secondary review source without exposing connector internals during normal use.

## UX shell model

The app header is a compact workspace shell, not a marketing hero. It shows the itinerary name, route, day count, current stage, and app version when an itinerary exists.

## Remaining risks

- Browser-level E2E coverage is still the right next layer for hosted Streamlit confidence.
- The visual editor and calculator components still have separate frontend commit/draft implementations.
- The workflow transaction layer centralizes current behavior, but a future deeper patch could make the whole app stage graph typed end-to-end.
