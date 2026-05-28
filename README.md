# Itinerary Creator

Streamlit app for turning pasted itinerary spreadsheet rows into polished A4 travel proposals with preview editing and PDF export.

## Run locally

```powershell
cd "C:\Users\DennisKålen\Desktop\itinerary_app\itinerary-creator"
python -m pip install -r requirements.txt
streamlit run app.py
```

## Test

```powershell
python -m pytest -q tests/test_regressions.py tests/test_images.py tests/test_pdf.py tests/test_real_fixture_quality_gate.py
python tests/test_rendered_pdf_quality.py
python -m compileall -q .
```

## Quality principles

The app should not render raw supplier/admin text directly into client-facing PDFs. Titles, descriptions, inclusions, exclusions, and route labels should pass through the parser, normalizer, content rules, sanitizers, and quality gates before rendering.
