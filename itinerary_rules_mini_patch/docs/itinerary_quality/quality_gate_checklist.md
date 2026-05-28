# Strict Quality Gate Checklist

Use this before sending any logic or layout patch.

## Test scope

Run the normal test suite:

```powershell
python .\tests\test_regressions.py
python .\tests\test_images.py
python .\tests\test_pdf.py
python -m py_compile <all app python files>
```

Run the real-input fixture bank and inspect generated outputs, not only function-level tests.

Representative fixture types:

- Iceland self-drive summer
- Norway short Oslo–Bergen–Ålesund
- Finland/Norway autumn Alta
- Finland/Norway winter family
- Norway/Sweden/Denmark summer
- Scandinavia autumn cruise

## PDF/preview inspection

Inspect every generated fixture output pessimistically.

Check:

- cover title and subtitle
- route list
- summary page
- Journey Arc length and accuracy
- every day page
- transport days
- optional add-ons
- inclusions page(s)
- exclusions page
- notes page
- preview/PDF parity for visual changes

## Hard fail conditions

Do not ship if any of these remain:

- optional add-on appears in normal inclusions
- self transfer appears in inclusions
- train transfer appears as an activity
- cruise leisure appears as commercial inclusion
- inclusion category spills without header or context
- departure transfer says `to your accommodation`
- day transfer title points to an intermediate stop instead of final destination
- same-day non-optional activity is missing
- not-included item appears under included section
- Journey Arc is long enough to wrap badly or reads generic/repetitive
- preview and PDF disagree materially

## Manual visual acceptance standard

If the output would not be comfortable to send to a client, the patch is not done.

## Before/after reporting

For every patch, report:

- files changed
- tests run
- fixture outputs checked
- old behavior
- new behavior
- known remaining limitations

