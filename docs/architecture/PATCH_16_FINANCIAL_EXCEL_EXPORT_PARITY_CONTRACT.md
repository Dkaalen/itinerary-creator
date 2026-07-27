# Patch 16 — Financial and Excel-export parity contract

## Boundary

The supported financial flow is:

`browser editing → canonical browser submission → CalculatorState → financial projection → workbook mutation plan → XLSX renderer`

The browser and Python engines remain independently parity-tested. Browser submissions convert visible supplier commission from percentage points to the canonical decimal once. Formula overrides are already canonical and retain formula text unchanged.

`calculator.financial_projection` is the single downstream calculation projection. It exposes immutable calculated rows, worksheet row identity, automatic/manual sales-price mode, and positive supplier-cost status. Export planning maps those decisions and does not evaluate formulas itself.

Both XLSX renderers consume the same immutable `WorkbookExportPlan`. They make no pricing, rate, VAT, commission, margin, chargeability, or cost-row-ID decisions.

## Workbook visibility and IDs

The visible calculation range ends ten rows after the final contentful Calculator row. Generated IDs, default currencies, blank preallocated rows, and internal workbook provenance do not count as content. Deliberate formulas do.

Commercial IDs are assigned in itinerary order only when the canonical projection reports a positive supplier cost in NOK. Free, leisure, zero-cost, negative-cost, and fully commissioned rows do not receive an ID.

## Preserved contracts

- Currency and exchange-rate behavior
- Formula and override precision
- Automatic and manual sales prices
- VAT and commission formulas
- Local Library provenance
- Intentional duplicate workbook rows
- Import/export round-trip behavior
- Template formulas, formatting, package metadata, and recalculation settings
- Non-mutation of Calculator source state
