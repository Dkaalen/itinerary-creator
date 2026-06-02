# Testing Workflow

The app has a mixed test suite: very fast parser/unit tests, broader itinerary
quality checks, and slower PDF/rendering checks.  Use the tiered commands below
so small patches do not require a full slow-suite run every time.

## Fast safety tests

Run after every code patch:

```powershell
.\scripts\run_fast_tests.ps1
```

This suite is intentionally small. It catches common breakage in parser helpers,
date handling, render caching, and broad stress follow-ups without doing expensive
PDF or large-fixture rendering.

## Medium quality tests

Run when you want broader confidence but do not need the full real-fixture suite:

```powershell
.\scripts\run_quality_tests.ps1
```

This is a curated parser/content/inclusions/transport set. It is broader than the fast suite but still avoids the longest real-fixture quality gates that can exceed hosted timeout limits.

## PDF/rendering tests

Run when changing PDF export, preview/PDF parity, final pages, image rendering,
or layout code:

```powershell
.\scripts\run_pdf_tests.ps1
```

## Full suite

Run locally before important pushes or releases:

```powershell
.\scripts\run_full_tests.ps1
```

The full suite can exceed short timeout limits in hosted patch-review
environments, so a timeout there does not automatically mean the app is broken.
Use the fast and targeted scripts to isolate failures quickly.

## Marker policy

Markers are assigned centrally in `tests/conftest.py` by test module name:

- `slow` for large real-fixture or PDF-heavy tests.
- `pdf` for tests that render or inspect PDF output.
- `quality` for broad real-fixture quality gates.

When adding new test files, update `tests/conftest.py` if the file belongs to one
of these categories.
