# Testing Workflow

The app has a mixed test suite: very fast parser/unit tests, focused subsystem
lanes, broader itinerary quality checks, and slower PDF/rendering checks. Use
the tiered commands below so small patches do not require a raw full-suite run
every time.

## Inspect available groups

To see the current validation lanes:

```powershell
python .\scripts\run_test_group.py --list-groups
```

To preview exactly what a group will run without executing pytest:

```powershell
python .\scripts\run_test_group.py full --plan
python .\scripts\run_test_group.py activity --plan
```

## Fast safety tests

Run after every code patch:

```powershell
.\scripts\run_fast_tests.ps1
```

This suite is intentionally small. It catches common breakage in parser helpers,
date handling, render caching, editor draft ownership, image audit contracts, and
broad stress follow-ups without doing expensive PDF or large-fixture rendering.

## Focused subsystem lanes

Use these when a patch touches a specific architecture area:

```powershell
.\scripts\run_parser_tests.ps1
.\scripts\run_activity_tests.ps1
.\scripts\run_architecture_tests.ps1
.\scripts\run_calculator_tests.ps1
.\scripts\run_editor_tests.ps1
.\scripts\run_image_tests.ps1
.\scripts\run_storage_tests.ps1
.\scripts\run_ui_tests.ps1
.\scripts\run_workflow_tests.ps1
```

These lanes are convenience validation gates. They may overlap with `fast` or
`quality`; overlap is intentional because a focused patch should be able to run
one clear command for the subsystem it changed. The calculator, storage, and
workflow lanes exist so hosted-app regressions do not depend on a raw full-suite
pytest run finishing before timeout.

### Bounded workflow lanes

Critical workflows also have small resumable lanes:

```powershell
python .\scripts\run_test_group.py calculator-browser
python .\scripts\run_test_group.py formulas
python .\scripts\run_test_group.py validation
python .\scripts\run_test_group.py workbook
python .\scripts\run_test_group.py calculator-realistic
python .\scripts\run_test_group.py project-management
python .\scripts\run_test_group.py rollback
python .\scripts\run_test_group.py cloud-lifecycle
python .\scripts\run_test_group.py reconstruction
python .\scripts\run_test_group.py generation
python .\scripts\run_test_group.py editor-pictures
python .\scripts\run_test_group.py generator
python .\scripts\run_test_group.py routes
python .\scripts\run_test_group.py inclusions
python .\scripts\run_test_group.py export
python .\scripts\run_test_group.py failure-modes
```

Use `--plan` to inspect stages and `--stage-range N-N` to rerun a specific stage. Calculator browser workflows are one node per stage; the other focused workflow stages contain no more than two modules. Every executable stage is capped at 45 seconds. Split an oversized catalogue stage instead of increasing that limit.

## Medium quality tests

Run when you want broader confidence but do not need the full real-fixture suite:

```powershell
.\scripts\run_quality_tests.ps1
```

This is a curated parser/content/inclusions/transport set. It is broader than
the fast suite but still avoids the longest real-fixture quality gates that can
exceed hosted timeout limits.

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

The full runner does not simply call raw `pytest -q`. It builds progress-tracked
stages, keeps slow/PDF-heavy targets near the end, and isolates known slow
stability targets so failures are easier to locate.

Raw full-suite pytest can exceed short timeout limits in hosted patch-review
environments, so a timeout there does not automatically mean the app is broken.
Use the fast and focused scripts to isolate failures quickly.

## Runtime policy

The app, CI, and local version files target Python 3.13. Keep `runtime.txt`,
`.python-version`, and `.github/workflows/tests.yml` aligned when changing the
hosted runtime.

## Marker policy

Markers are declared in `pytest.ini` and assigned centrally in `tests/conftest.py` from the named group catalogue:

- `slow` for large real-fixture or PDF-heavy tests.
- `pdf` for tests that render or inspect PDF output.
- `quality` for broad real-fixture quality gates.

When adding new heavy test files, update `scripts/test_groups.py` and
`tests/conftest.py` if the file belongs to one of these marker categories. For
ordinary subsystem tests, add the file to the most relevant focused lane in
`scripts/test_groups.py` so future patches can validate it with one command.
