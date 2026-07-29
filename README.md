# Itinerary Creator

Streamlit app for turning pasted itinerary spreadsheet rows into polished A4 travel proposals with preview editing and PDF export.

## Run locally

```powershell
cd path/to/itinerary-creator
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
streamlit run app.py
```

## Configure secrets

Copy `.streamlit/secrets.example.toml` to `.streamlit/secrets.toml` for local development and replace the placeholders through your local secret store. The real `secrets.toml` is ignored and must never be committed. Configure the same values in Streamlit Cloud's protected secrets before deployment. If a credential is ever committed, rotate or revoke it; deleting the file from the latest commit is not sufficient.

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

Focused workflow lanes can be listed or run directly:

```powershell
python .\scripts\run_test_group.py calculator-browser --plan
python .\scripts\run_test_group.py validation
python .\scripts\run_test_group.py project-management
python .\scripts\run_test_group.py editor-pictures
```

## Build a clean handoff ZIP

For ChatGPT handoff or lightweight backups, do not manually compress the whole working tree. Build the standard source-only package instead:

```powershell
python scripts/build_handoff_zip.py --output "..\itinerary-creator-git-handoff.zip"
```

The handoff ZIP excludes Git metadata, caches, generated outputs, old ZIP files, and local credential files while keeping source files and safe examples such as `.streamlit/secrets.example.toml`.

When a patch deletes files, apply the deletion with `git rm "path\to\file.py"` before committing so the file is removed locally and on GitHub after push.


## Patch handoff standard

The uploaded ZIP is the source of truth for ChatGPT patch work. Use the clean handoff builder above instead of manual compression so local secrets, Git metadata, caches, bytecode, generated outputs, and old ZIP files stay out of the handoff. Before sharing or applying a handoff ZIP, it can be checked with:

```powershell
python scripts/validate_handoff_zip.py "..\itinerary-creator-git-handoff.zip"
```

Each completed patch should be validated, should list changed/new and deleted files, and should be applied with explicit file paths rather than `git add .`.

## Quality principles

The app should not render raw supplier/admin text directly into client-facing PDFs. Titles, descriptions, inclusions, exclusions, and route labels should pass through the parser, normalizer, content rules, sanitizers, and quality gates before rendering.

## Local Excel Library

Calculator autocomplete reads only from `data/Calculation-template-Inputs-fixed-outline-restored.xlsx`. Update or replace that workbook at the same path and redeploy through GitHub/Streamlit. No Google Sheets or Supabase connection is used for Local Library fetching.

The stable `calculator.library_workbook` loader orchestrates separate schema, formula/cache, row-validation, diagnostic, and immutable-model owners. Workbook fingerprint caching and worksheet/source-row identity remain part of the public loading contract.

## Supabase project storage

Saved itinerary projects use the repository-owned Supabase boundary in `project_storage/`. Database changes are additive migrations under `supabase/migrations/`; apply them through the Supabase SQL Editor before deploying UI code that depends on them. Project owner/folder labels are organizational metadata only and do not provide authentication or authorization. The production Local Library remains the bundled Excel workbook and is not stored in Supabase.

## Calculator frontend

The browser Calculator keeps one deterministic script-loading order. Editing, calculations, rendering, and actions have separate implementation owners while the existing browser state, recovery, and backend-message contracts remain stable.

## Destination content and Journey Arc summaries

Destination lookup, arrival, leisure, travel-day, seasonal-profile, and fallback rules have separate owners behind the existing public facades. Journey Arc experience wording is assembled through separate source extraction, prioritization, duplicate control, phrasing, and composition modules.

## Transport route facts

Route parsing, row-level endpoint inference, validation, intermediate stops, terminal normalization, caching, and final route-fact composition have separate owners. Multi-leg routes keep intermediate stops separate from the final destination.

## Calculator backup

The calculator page can export a JSON backup and reopen it later. This is separate from the Excel calculation export and is meant for restoring editable calculator rows before generating the itinerary.
