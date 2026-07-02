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

Fast patch checks:

```powershell
.\scripts\run_fast_tests.ps1
```

Full suite before important pushes:

```powershell
.\scripts\run_full_tests.ps1
python -m compileall -q .
```

See `docs/testing-workflow.md` for the full tiered workflow.

## Build a clean handoff ZIP

For ChatGPT handoff or lightweight backups, do not manually compress the whole working tree. Build the standard source-only package instead:

```powershell
python scripts/build_handoff_zip.py --output "..\itinerary-creator-git-handoff.zip"
```

The handoff ZIP excludes Git metadata, caches, generated outputs, old ZIP files, and local credential files while keeping source files and safe examples such as `.streamlit/secrets.example.toml`.

When a patch deletes files, apply the deletion with `git rm "path\to\file.py"` before committing so the file is removed locally and on GitHub after push.

## Quality principles

The app should not render raw supplier/admin text directly into client-facing PDFs. Titles, descriptions, inclusions, exclusions, and route labels should pass through the parser, normalizer, content rules, sanitizers, and quality gates before rendering.

## Local Library Google Sheets

The calculator Local Library uses Google Sheets when Streamlit secrets are configured. Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` locally, add the service account values, and share the spreadsheet with the service account email.

If secrets are missing, the app uses the bundled read-only fixture instead of crashing.

## Calculator backup

The calculator page can export a JSON backup and reopen it later. This is separate from the Excel calculation export and is meant for restoring editable calculator rows before generating the itinerary.
