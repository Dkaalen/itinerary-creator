# Patch 17 — Itinerary continuity authority

## Boundary

The supported flow is:

`normalized rows → route/timeline facts → ItineraryContinuityReport → copy, warnings, quality, editor, preview, PDF, QA and health projections`

`itinerary_generation.itinerary_continuity` is the sole owner of itinerary-level geographic and temporal continuity decisions. Its immutable report contains findings and canonical per-day state, including start/end/overnight places, chapter city, visit history, genuine returns, day-trip returns, arrivals, stay continuation, same-city accommodation changes, and overlap findings.

Route parsing, source product classification, copywriting, images, financial logic, sanitation and renderer layout remain separate owners.

## Consumer contract

- `destination_visit_memory` and `copy.visit_context` project the report; they do not reconstruct geography.
- Day-state and arrival-intent copy consume canonical visit and stay decisions.
- The structured document stores the report.
- Render, editor and visible preview/PDF documents retain the same immutable report instance.
- Journey Arc uses canonical chapter cities, so an excursion does not become a false stay chapter.
- Prepared client quality and real-output QA use the report for continuity and return wording.
- Health reporting projects canonical genuine returns instead of scanning a private city sequence.

Validation may build a report before output edits. When user edits change dates, locations or movement, render preparation intentionally creates the new report for the edited facts. All consumers of that prepared context share it.
