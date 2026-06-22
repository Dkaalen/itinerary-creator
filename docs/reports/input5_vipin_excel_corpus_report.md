# INPUT5 Vipin Excel Corpus Regression Report

Purpose: run the real messy Nordic calculator corpus through parser and editable-title generation, then log risky outputs for regression hardening.

## Summary

- Corpus rows checked: 5557
- Parsed output rows: 5438
- Generated editable titles checked: 4205
- Workbooks: 2
- Sheets with extracted rows: 307
- Parser exceptions: 0
- Rows skipped by parser: 119
- Average parser confidence: 97.3%
- Rows under 80 confidence: 210
- Whole-corpus generation smoke: passed
- Bad-output log: `docs/reports/input5_vipin_excel_bad_outputs.jsonl`

## INPUT5 before/after output-risk counts

- overlong_title: 306 → 165
- activity_text_used_as_title: 272 → 124
- missing_parsed_city: 19 → 9
- unexpected_skip: 38 → 35
- missing_route_origin flag: 116 → 106
- missing_route_destination flag: 92 → 82

Source-quality warnings such as missing source city/day/date are still reported because they reflect incomplete workbook rows, not generated title failures.

## Bad-output counts

- missing_source_city: 381
- overlong_title: 165
- activity_text_used_as_title: 124
- missing_source_date: 87
- missing_source_day: 85
- non_itinerary_type: 65
- unexpected_skip: 35
- missing_source_type: 21
- missing_parsed_city: 9

## Parser review flags

- very_long_supplier_text: 324
- missing_route_origin: 106
- missing_hotel_name: 102
- missing_room_category: 87
- missing_route_destination: 82
- missing_city: 9
- weak_title: 7
- missing_hotel_nights: 2

## Top source types

- transfer: 2001
- activity: 1891
- hotel: 1141
- day overview: 211
- leisure: 86
- per pax: 52
- arrival: 32
- [blank]: 21
- one pax: 13
- day 1: 11
- day 3: 10
- departure: 9
- notes: 9
- day 5: 8
- day 9: 8
- 4000.0: 7
- day 6: 7
- day 7: 7
- day 4: 6
- day 2: 5
- day 8: 5
- day 10: 5
- day 11: 5
- day: 3
- 46351.0: 1
- 46355.0: 1
- 46357.0: 1
- single room cost: 1

## Worst-case samples

### overlong_title
- Vipin Calculator Nordic 2.xlsx::10174.2::R9 | type='Activity' | title='Hike Vatnajökull Glacier & Sail Glacier Lagoon Your next destination will be the Glacier Lagoon Jökulsárlón with a few stops along the way. Jökulsárlón is formed by the receding glacial tongue Breiðamerkurjökull where huge chunks of ice break away and float lazily out to sea. No iceberg is the same, and each is characterized by different blue and white shades scarred with volcanic ash from historical eruptions. During your visit to the Glacier Lagoon' | generated='Hike Vatnajökull Glacier & Sail Glacier Lagoon Your next destination will be the Glacier Lagoon Jökulsárlón with a few stops along the way. Jökulsárlón is formed by the receding glacial tongue Breiðamerkurjökull where huge chunks of ice break away and float lazily out to sea. No iceberg is the same, and each is characterized by different blue and white shades scarred with volcanic ash from historical eruptions. During your visit to the Glacier Lagoon' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10174::R8 | type='Activity' | title='Explore Snæfellsnes Prepare to explore amazing things like, lava fields, dreamy waterfalls, dark caves, black and white beaches, historical locations and the mighty Snæfellsjökull Glacier of the west. The glacier played an important role in the novel Journey to the Centre of the Earth, by Jules Verne, where it was the opening point to a great underground journey' | generated='Explore Snæfellsnes Prepare to explore amazing things like, lava fields, dreamy waterfalls, dark caves, black and white beaches, historical locations and the mighty Snæfellsjökull Glacier of the west. The glacier played an important role in the novel Journey to the Centre of the Earth, by Jules Verne, where it was the opening point to a great underground journey' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10174::R9 | type='Activity' | title='Discover the Golden Circle You will visit the famous Þingvellir National Park, Gullfoss, Geysir and the surrounding Geothermal Area. In Þingvellir National Park, Iceland’s first parliament was founded in the year 930 AD. Also, Þingvellir National Park is a UNESCO World Heritage due to its visible tectonic plates on the surface. At Haukadalur Geothermal Area' | generated='Discover the Golden Circle You will visit the famous Þingvellir National Park, Gullfoss, Geysir and the surrounding Geothermal Area. In Þingvellir National Park, Iceland’s first parliament was founded in the year 930 AD. Also, Þingvellir National Park is a UNESCO World Heritage due to its visible tectonic plates on the surface. At Haukadalur Geothermal Area' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10174::R10 | type='Activity' | title='Hike South Coast Waterfalls & Glacier The first stop is at Seljalandsfoss waterfall where you can walk behind the tumbling water flow and feel the vibrations of the water hitting the ground' | generated='Hike South Coast Waterfalls & Glacier The first stop is at Seljalandsfoss waterfall where you can walk behind the tumbling water flow and feel the vibrations of the water hitting the ground' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10174::R11 | type='Activity' | title='Explore Jökulsárlón & Ice Caves A 200m deep glacial lake fed by Breiðamerkurjökull, an outlet glacier of Europe’s largest glacier. Fed enormous icebergs all year round the lagoon is usually filled with ice that floats south. We walk alongside the Glacier Lagoon enjoying the magnificent views and dead silence of Icelandic nature. Diamond Beach On the other side of the road the icebergs from Jökulsárlón float into the Atlantic Ocean where they are quickly thrown back to shore by the tide and winds. This black sand beach is full of smaller ice rocks in all shapes and sizes, sparkling like diamonds in the daylight. The ice itself comes in all shades of white and blue forming beautiful contrasts, guaranteed to make your Instagram account pop! And to make the experience even better we end with an Ice Cave tour from Jökulsárlón, where' | generated='Explore Jökulsárlón & Ice Caves A 200m deep glacial lake fed by Breiðamerkurjökull, an outlet glacier of Europe’s largest glacier. Fed enormous icebergs all year round the lagoon is usually filled with ice that floats south. We walk alongside the Glacier Lagoon enjoying the magnificent views and dead silence of Icelandic nature. Diamond Beach On the other side of the road the icebergs from Jökulsárlón float into the Atlantic Ocean where they are quickly thrown back to shore by the tide and winds. This black sand beach is full of smaller ice rocks in all shapes and sizes, sparkling like diamonds in the daylight. The ice itself comes in all shades of white and blue forming beautiful contrasts, guaranteed to make your Instagram account pop! And to make the experience even better we end with an Ice Cave tour from Jökulsárlón, where' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10173::R33 | type='Activity' | title='Excursion to Tallinn - Helsinki Port transfers included (hotel Pick-up and drop-off) - Self guided tour of Old Town Tallinn' | generated='Excursion to Tallinn - Helsinki Port transfers included (hotel Pick-up and drop-off) - Self guided tour of Old Town Tallinn' | reason=Parsed title is over 100 characters.

### activity_text_used_as_title
- Vipin Calculator Nordic 2.xlsx::10174.2::R9 | type='Activity' | title='Hike Vatnajökull Glacier & Sail Glacier Lagoon Your next destination will be the Glacier Lagoon Jökulsárlón with a few stops along the way. Jökulsárlón is formed by the receding glacial tongue Breiðamerkurjökull where huge chunks of ice break away and float lazily out to sea. No iceberg is the same, and each is characterized by different blue and white shades scarred with volcanic ash from historical eruptions. During your visit to the Glacier Lagoon' | generated='Hike Vatnajökull Glacier & Sail Glacier Lagoon Your next destination will be the Glacier Lagoon Jökulsárlón with a few stops along the way. Jökulsárlón is formed by the receding glacial tongue Breiðamerkurjökull where huge chunks of ice break away and float lazily out to sea. No iceberg is the same, and each is characterized by different blue and white shades scarred with volcanic ash from historical eruptions. During your visit to the Glacier Lagoon' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10174::R8 | type='Activity' | title='Explore Snæfellsnes Prepare to explore amazing things like, lava fields, dreamy waterfalls, dark caves, black and white beaches, historical locations and the mighty Snæfellsjökull Glacier of the west. The glacier played an important role in the novel Journey to the Centre of the Earth, by Jules Verne, where it was the opening point to a great underground journey' | generated='Explore Snæfellsnes Prepare to explore amazing things like, lava fields, dreamy waterfalls, dark caves, black and white beaches, historical locations and the mighty Snæfellsjökull Glacier of the west. The glacier played an important role in the novel Journey to the Centre of the Earth, by Jules Verne, where it was the opening point to a great underground journey' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10174::R9 | type='Activity' | title='Discover the Golden Circle You will visit the famous Þingvellir National Park, Gullfoss, Geysir and the surrounding Geothermal Area. In Þingvellir National Park, Iceland’s first parliament was founded in the year 930 AD. Also, Þingvellir National Park is a UNESCO World Heritage due to its visible tectonic plates on the surface. At Haukadalur Geothermal Area' | generated='Discover the Golden Circle You will visit the famous Þingvellir National Park, Gullfoss, Geysir and the surrounding Geothermal Area. In Þingvellir National Park, Iceland’s first parliament was founded in the year 930 AD. Also, Þingvellir National Park is a UNESCO World Heritage due to its visible tectonic plates on the surface. At Haukadalur Geothermal Area' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10174::R10 | type='Activity' | title='Hike South Coast Waterfalls & Glacier The first stop is at Seljalandsfoss waterfall where you can walk behind the tumbling water flow and feel the vibrations of the water hitting the ground' | generated='Hike South Coast Waterfalls & Glacier The first stop is at Seljalandsfoss waterfall where you can walk behind the tumbling water flow and feel the vibrations of the water hitting the ground' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10174::R11 | type='Activity' | title='Explore Jökulsárlón & Ice Caves A 200m deep glacial lake fed by Breiðamerkurjökull, an outlet glacier of Europe’s largest glacier. Fed enormous icebergs all year round the lagoon is usually filled with ice that floats south. We walk alongside the Glacier Lagoon enjoying the magnificent views and dead silence of Icelandic nature. Diamond Beach On the other side of the road the icebergs from Jökulsárlón float into the Atlantic Ocean where they are quickly thrown back to shore by the tide and winds. This black sand beach is full of smaller ice rocks in all shapes and sizes, sparkling like diamonds in the daylight. The ice itself comes in all shades of white and blue forming beautiful contrasts, guaranteed to make your Instagram account pop! And to make the experience even better we end with an Ice Cave tour from Jökulsárlón, where' | generated='Explore Jökulsárlón & Ice Caves A 200m deep glacial lake fed by Breiðamerkurjökull, an outlet glacier of Europe’s largest glacier. Fed enormous icebergs all year round the lagoon is usually filled with ice that floats south. We walk alongside the Glacier Lagoon enjoying the magnificent views and dead silence of Icelandic nature. Diamond Beach On the other side of the road the icebergs from Jökulsárlón float into the Atlantic Ocean where they are quickly thrown back to shore by the tide and winds. This black sand beach is full of smaller ice rocks in all shapes and sizes, sparkling like diamonds in the daylight. The ice itself comes in all shades of white and blue forming beautiful contrasts, guaranteed to make your Instagram account pop! And to make the experience even better we end with an Ice Cave tour from Jökulsárlón, where' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10173::R33 | type='Activity' | title='Excursion to Tallinn - Helsinki Port transfers included (hotel Pick-up and drop-off) - Self guided tour of Old Town Tallinn' | generated='Excursion to Tallinn - Helsinki Port transfers included (hotel Pick-up and drop-off) - Self guided tour of Old Town Tallinn' | reason=Parsed title looks like supplier prose or activity body text.

### missing_parsed_city
- Vipin Calculator Nordic 2.xlsx::10168::R11 | type='Activity' | title='City Highlights, Santa Claus Village & Husky-Reindeer Safari' | generated='City Highlights, Santa Claus Village & Husky-Reindeer Safari' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10150::R6 | type='Activity' | title='Group TOur' | generated='Group TOur' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10150::R11 | type='Transfer' | title='Rental Car' | generated='Rental Car' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10131::R10 | type='Transfer' | title='46206' | generated='46206' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10126v2::R20 | type='Activity' | title='Leisure Day' | generated='Leisure Day' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10119::R10 | type='Activity' | title='Self Planned' | generated='Self Planned' | reason=Parsed row is missing city/area.

### unexpected_skip
- Vipin Calculator Nordic 2.xlsx::New Template::R69 | type='Day' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.
- Vipin Calculator Nordic 2.xlsx::10175.2::R15 | type='Transfer' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.
- Vipin Calculator Nordic 2.xlsx::10155::R4 | type='Transfer' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.
- Vipin Calculator Nordic 2.xlsx::10149::R5 | type='Hotel' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.
- Vipin Calculator Nordic 2.xlsx::10142::R104 | type='46351.0' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.
- Vipin Calculator Nordic 2.xlsx::10142::R109 | type='46355.0' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.

### missing_source_type
- Vipin Calculator Nordic 2.xlsx::10168::R7 | type='' | title='' | generated='' | reason=Source row has no type value.
- Vipin Calculator Nordic 2.xlsx::10145v2::R18 | type='' | title='' | generated='' | reason=Source row has no type value.
- Vipin Calculator Nordic 2.xlsx::10127::R4 | type='' | title='' | generated='' | reason=Source row has no type value.
- Vipin Calculator Nordic 2.xlsx::10127::R12 | type='' | title='' | generated='' | reason=Source row has no type value.
- Vipin Calculator Nordic 2.xlsx::10127::R13 | type='' | title='' | generated='' | reason=Source row has no type value.
- Vipin Calculator Nordic 2.xlsx::10127::R14 | type='' | title='' | generated='' | reason=Source row has no type value.

### non_itinerary_type
- Vipin Calculator Nordic 2.xlsx::10085 v2 Group Tour ::R74 | type='per pax' | title='' | generated='' | reason=Source row type looks like a calculator/cost row.
- Vipin Calculator Nordic 2.xlsx::10085 v2 Group Tour ::R75 | type='per pax' | title='' | generated='' | reason=Source row type looks like a calculator/cost row.
- Vipin Calculator Nordic 2.xlsx::10085 v2 Group Tour ::R76 | type='per pax' | title='' | generated='' | reason=Source row type looks like a calculator/cost row.
- Vipin Calculator Nordic 2.xlsx::10085 v2 Group Tour ::R77 | type='per pax' | title='' | generated='' | reason=Source row type looks like a calculator/cost row.
- Vipin Calculator Nordic 2.xlsx::10085 v2 Group Tour ::R78 | type='One Pax' | title='' | generated='' | reason=Source row type looks like a calculator/cost row.
- Vipin Calculator Nordic 2.xlsx::10085 v2 Group Tour ::R88 | type='per pax' | title='' | generated='' | reason=Source row type looks like a calculator/cost row.

### missing_source_city
- Vipin Calculator Nordic 2.xlsx::10168::R5 | type='Hotel' | title='' | generated='' | reason=Source row has no city/area value.
- Vipin Calculator Nordic 2.xlsx::10168::R6 | type='Activity' | title='' | generated='' | reason=Source row has no city/area value.
- Vipin Calculator Nordic 2.xlsx::10168::R7 | type='' | title='' | generated='' | reason=Source row has no city/area value.
- Vipin Calculator Nordic 2.xlsx::10168::R9 | type='Hotel' | title='' | generated='' | reason=Source row has no city/area value.
- Vipin Calculator Nordic 2.xlsx::10168::R10 | type='Activity' | title='' | generated='' | reason=Source row has no city/area value.
- Vipin Calculator Nordic 2.xlsx::10168::R11 | type='Activity' | title='' | generated='' | reason=Source row has no city/area value.

### missing_source_day
- Vipin Calculator Nordic 2.xlsx::10150::R12 | type='Transfer' | title='' | generated='' | reason=Source row has no day value.
- Vipin Calculator Nordic 2.xlsx::10073::R13 | type='Transfer' | title='' | generated='' | reason=Source row has no day value.
- Vipin Calculator Nordic 2.xlsx::10073::R25 | type='Activity' | title='' | generated='' | reason=Source row has no day value.
- Vipin Calculator Nordic 2.xlsx::10073::R86 | type='Day 1' | title='' | generated='' | reason=Source row has no day value.
- Vipin Calculator Nordic 2.xlsx::10073::R87 | type='Day 1' | title='' | generated='' | reason=Source row has no day value.
- Vipin Calculator Nordic 2.xlsx::10073::R88 | type='Day 1' | title='' | generated='' | reason=Source row has no day value.

### missing_source_date
- Vipin Calculator Nordic 2.xlsx::10150::R12 | type='Transfer' | title='' | generated='' | reason=Source row has no date value.
- Vipin Calculator Nordic 2.xlsx::10142::R104 | type='46351.0' | title='' | generated='' | reason=Source row has no date value.
- Vipin Calculator Nordic 2.xlsx::10114v2::R19 | type='Leisure' | title='' | generated='' | reason=Source row has no date value.
- Vipin Calculator Nordic 2.xlsx::10073::R13 | type='Transfer' | title='' | generated='' | reason=Source row has no date value.
- Vipin Calculator Nordic 2.xlsx::10073::R25 | type='Activity' | title='' | generated='' | reason=Source row has no date value.
- Vipin Calculator Nordic 2.xlsx::10073::R86 | type='Day 1' | title='' | generated='' | reason=Source row has no date value.
