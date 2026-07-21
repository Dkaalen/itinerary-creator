# Calculator financial rules

## Authority

`calculator/financial_rules.py` is the single versioned contract for financial precision and margin behavior. Python calculations remain authoritative in `calculator/cell_formula_engine.py`; the browser receives the contract through `app_modules/calculator_component_payload.py` and executes an independently parity-tested preview in `calculator_grid_math.js`.

The contract version is `financial-v1`.

## Precision

| Kind | Decimal places |
| --- | ---: |
| Money | 2 |
| Exchange rate | 6 |
| Percentage or ratio | 6 |

Python and browser calculations use decimal half-away-from-zero rounding. Supplier commission is stored as a ratio, such as `0.20`, and displayed as `20` in the browser.

## Calculation order

For each row:

1. Gross supplier price is the supplier unit price multiplied by units.
2. Net supplier price applies supplier commission to gross supplier price.
3. Net NOK cost applies the supplier exchange rate unless explicitly overridden.
4. Sales price uses the manual sales price when supplied; otherwise it uses the automatic rule.
5. Sales NOK total applies units and the sales exchange rate unless explicitly overridden.
6. GP NOK is sales NOK total minus net NOK cost.
7. GP percentage is GP NOK divided by sales NOK total.
8. VAT buckets and totals use the same rounded row results.

Explicit A1 formula overrides participate in the same dependency graph and precision rules as numeric inputs.

## Target GP margin shortcuts

The 20%, 15%, and 10% shortcuts solve the sales price per unit from actual `net_price_nok`. This includes supplier commission, quantity, exchange rates, and explicit upstream cost overrides. Applying a target clears downstream sales-derived overrides so they cannot silently defeat the requested GP. “Use automatic” restores automatic sales-price behavior.

## State and project persistence

Financial inputs and formula strings are serialized through the Calculator state schema. Saved-project reconstruction must reproduce the same row calculations and totals after reload. Calculated outputs are reconstructed rather than treated as an independent source of truth.

## Excel import and export

The canonical export plan applies the same precision policy to numeric rates, commission, and formula overrides. User formulas are exported as `ROUND((expression), digits)` so Excel agrees with Python and browser precision. Import removes only this exact app-generated wrapper and restores the original editable formula.

Total money formulas are rounded to two decimals. Percentage totals remain ratios. Workbook formulas, Python, browser previews, imported state, and reconstructed projects are parity-tested against the shared fixture bank.

## Required parity coverage

`tests/fixtures/calculator_financial_parity_cases.json` covers:

- supplier commission and VAT
- NOK, EUR, USD, and cross-currency rows
- quantities and zero-unit behavior
- automatic and manual sales prices
- A1 formulas and cross-row references
- explicit calculated-field overrides
- rate and percentage precision
- half-away-from-zero rounding
- project save/reload
- Excel export/import
- target GP margin shortcuts
