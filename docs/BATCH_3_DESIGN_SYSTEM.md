# Batch 3 — App Design System and Workspace Redesign

This batch changes the app design direction from a repainted Streamlit form to a quieter itinerary workspace.

## Design intent

- Nordic/Japanese minimalism: calm, precise, warm, and practical.
- No deep green primary action color.
- No oversized colored pill buttons as the main layout device.
- Clear workspace structure: document creation, tools, saved projects, calculator, and export readiness.
- Use layout, spacing, typography, and quiet contrast to guide the user instead of loud color blocks.

## Main changes

- The input page now opens with a product-style itinerary studio hero instead of a stacked form.
- Calculator and saved-project tools are moved into a side workspace, making alternate starts easier to understand.
- The input form is split into document details, source content, and generation actions.
- The calculator and Local Library pages now have first-class workspace headers.
- The app palette now uses paper, stone, sumi ink, and muted taupe accents.
- Primary buttons use quiet ink styling instead of the previous deep green gradient.
- Calculator grid styling now matches the app palette.

## Guardrails

- `tests/test_design_system_regression.py` prevents the old deep green primary style from returning in the app shell and calculator grid.
- `tests/test_ui_style_contrast.py` now checks the quieter palette and button contrast.
- Existing workflow tests still verify that design changes did not alter the main itinerary flow.

## Still intentionally not done

This batch does not redesign the visual editor internals or PDF document theme. Those are separate surfaces with their own contracts and should be changed only with preview/PDF parity testing.
