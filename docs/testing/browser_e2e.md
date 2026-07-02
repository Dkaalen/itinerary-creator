# Browser E2E test foundation

The browser E2E suite is opt-in and uses `pytest-playwright` against the real Streamlit workflow.

Covered workflow targets:

- generate itinerary
- add pictures
- edit text
- edit image crop/centering
- create PDF first click
- download PDF
- open saved project file
- reopen then create PDF
- no stale editor export

Run locally after installing Playwright browsers:

```powershell
pip install -r requirements-dev.txt
python -m playwright install chromium
$env:ITINERARY_RUN_BROWSER_E2E="1"
pytest tests/e2e -q
```

To point tests at an already running app:

```powershell
$env:ITINERARY_E2E_APP_URL="http://localhost:8501"
pytest tests/e2e -q
```
