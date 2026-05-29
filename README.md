# Itinerary Creator

Streamlit app for turning pasted itinerary spreadsheet rows into polished A4 travel proposals with preview editing and PDF export.

## Run locally

```powershell
cd path/to/itinerary-creator
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
streamlit run app.py
```

## Test

```powershell
python -m pytest tests/
python -m compileall -q .
```

## Quality principles

The app should not render raw supplier/admin text directly into client-facing PDFs. Titles, descriptions, inclusions, exclusions, and route labels should pass through the parser, normalizer, content rules, sanitizers, and quality gates before rendering.
