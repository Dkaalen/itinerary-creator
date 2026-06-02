# Quality Stress Input Banks

This folder stores future regression-fixture banks for the Itinerary App.

The files are data only. They are intentionally not active pytest tests until a patch promotes selected examples into focused regression coverage.

Current banks:
- `accommodation/` — hotel, lodge, cruise cabin, train cabin, room quantity, bed type, meal plan, and messy accommodation examples.
- `activities_compound/` — city tours, compound day excursions, scenic journeys, multi-stop tours, and messy activity rows.
- `optional_commercial/` — optional add-ons, optional hotels/transfers, self transfers, and included-on-request wording.
- `flights_self_arranged/` — included flights, self-arranged flights, cost-not-included variants, and flight-row typo cleanup.
- `leisure_arrival_departure/` — leisure rows, arrival/departure logistics, and mixed travel/free-time examples.
- `metadata_content_cleanup/` — inline labels, highlights/stops, pipe metadata, supplier CTA, and raw-content cleanup examples.

Future planned banks:
- transport stress promotion
- PDF layout and rendered-text quality
