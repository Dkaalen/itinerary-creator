# Real Input Fixture Expectations

This document describes the expected behavior for the real-input regression bank.

## Iceland self-drive summer

Expected:

- Title: `Iceland Summer Journey`
- Travel style mentions self-drive.
- Rental block is compressed and does not repeat pick-up.
- Blue Lagoon and Sky Lagoon are admission/wellness experiences, not guided tours.
- `Fosshotel Glacier Lagoon` parses as hotel name.
- `Duration: 2.5–3.5 hours` is preserved for whale watching.
- Optional or not-included items are separated.
- No `Bluelagoon`, `National Park National Park`, `Ranua Wildlife Park`, or breakfast duplication.
- Self transfers do not appear in inclusions.

## Norway short Oslo–Bergen–Ålesund

Expected:

- Title: `Norway Summer Journey`.
- Route: Oslo · Bergen · Ålesund.
- `Train : Oslo to Bergen` becomes rail transport, not an activity.
- Day title: `Train to Bergen`.
- Travel arrangement: `Scenic Train Transfer from Oslo to Bergen`.
- Inclusions: rail appears under `Rail journeys`, not `Activities & experiences`.
- Overnight cruise from Bergen to Ålesund preserves cabin and arrival details.
- Ålesund arrival day includes cruise arrival when the arrival time is known.

## Finland/Norway autumn Alta

Expected:

- Title: `Nordic Autumn Journey`.
- Day 4 includes both Santa/Reindeer and evening Northern Lights activity.
- Day 8 title: `Coach Transfer to Alta`.
- Travel arrangement: `Panoramic Coach Transfer from Tromsø to Alta` when source says panoramic.
- Self transfers appear only on day logistics, never in inclusions.
- Optional Alta whale safari appears under `Optional add-ons`, not normal inclusions.
- Exclusions include self-arranged or optional cost language when relevant.
- Reindeer/Sámi description does not call it a Northern Lights hunt.

## Scandinavia autumn cruise

Expected:

- Title: `Scandinavian Autumn Journey`.
- Day 4 title: `Train to Stockholm`, not `Train to Malmö`.
- Travel arrangement: `Scenic Train Transfer from Copenhagen to Stockholm, via Malmö`.
- Day 8 cruise intro points towards Bergen, not Kirkenes.
- Cruise leisure days say `Spend time at leisure onboard the cruise` but are not inclusions.
- Cruise arrival to Bergen preserves arrival time.
- Ferries & cruises inclusion contains the actual cruise product and cabin/meal plan, not every leisure day.
- Inclusion categories do not orphan bullets on a new page.

## Norway/Sweden/Denmark summer

Expected:

- Title: `Scandinavian Summer Journey`.
- Country/region detection does not fall back to Nordic if only Scandinavian countries are present.
- Self-arranged flights do not appear in inclusions.
- Flight wording includes route and via city when available.
- Train/rail, cruise/ferry, private transfer, and flight inclusions are in the correct categories.

## Finland/Norway winter variants

Expected:

- Title: `Nordic Winter Journey`.
- Northern Lights and winter activity descriptions are relevant to the activity and destination.
- Hotel family-room parsing stays intact.
- Transfer direction and destination are correct.
- Self transfers do not appear as inclusions.

