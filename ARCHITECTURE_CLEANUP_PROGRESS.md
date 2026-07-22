# Architecture Cleanup Progress

This file is the current handoff and workflow contract expected by tests and project deliveries.

Use **patch** for each implementation unit. When returning changed files, stage explicit paths:

```powershell
git add -- $files
```

When files are deleted, stage each verified deletion explicitly:

```powershell
git rm --ignore-unmatch -- path/to/deleted_file.py
```

Do not use broad accidental staging such as `git add .` or `git add -A`.

## Architecture principle

One file should have one clear responsibility. Compatibility facades are allowed only to preserve stable import paths; they must not contain duplicate business logic.

Historical patch notes are archived at `docs/archive/ARCHITECTURE_CLEANUP_PROGRESS.md`.

## Patch 21 — Calculator frontend split

The Calculator frontend now has separate owners for editing/caret/keyboard/commit behavior, formulas/currency/formatting, toolbar/grid/status/suggestion rendering, and Excel/sales/submission/shortcut actions. The deterministic script order, browser state authorities, backend protocol, global browser APIs, and visual behavior remain stable.

## Patch 22 — Day-intro writer split

The fact-based day-intro writer now has separate owners for planning context, destination awareness, phrase selection, return-visit repetition protection, date-derived seasonal context, and decision rendering. The public `day_intro_writer` import path remains stable.

## Patch 23 — Destination-content split

Nordic destination content now has separate owners for season profiles, canonical lookup and fallback, Journey Arc copy, arrival focus, leisure copy, travel-day copy, and deterministic prose variants. Existing destination facades remain stable.

## Patch 24 — Experience-summary split

Compact Journey Arc summaries now have separate owners for source extraction, ordered prioritization, stable duplicate control, client-facing phrasing, and final composition. The public `describe_city_experience` API remains stable.

## Patch 25 — Route-point split

Transport routes now have separate owners for parser place values, generic route parsing, row-aware endpoint inference, canonical-field validation, intermediate stops, terminal/hub normalization, cached public access, and route-fact composition. Existing parser and transport import paths remain stable.

## Patch 26 — Remaining ownership-heavy modules

The remaining production audit identified one genuine split target: the Local Library workbook loader. Workbook models, schema/currency extraction, formula/cache inspection, row validation, diagnostics, and cached orchestration now have separate owners while `calculator.library_workbook` keeps its stable public API. Other reviewed large modules were retained where responsibilities were cohesive.

## Patch 27 — Complete bounded test groups

Every active pytest module belongs to a named group. The former 15-module full-only backlog is zero, with no stale or duplicate catalogue entries. Broad Calculator and Storage lanes own release coverage, while focused lanes cover browser workflows, formulas, validation, workbook handling, realistic use, project management, rollback, cloud lifecycle, reconstruction, generation, and editor/picture integration. Browser workflows are explicit node-level stages; focused stages have hard timeouts and checkpoint/resume support.

## Patch 28 — Full replay and delivery

Patch 28 replays the architecture, Calculator browser, Local Library, formulas, workbook, project lifecycle, reconstruction, generation, editor/pictures, PDF, startup, and failure-path gates on a fresh extraction. Delivery contains only modified and newly added repository files, plus an exact deletion list and explicit-path PowerShell staging command.
