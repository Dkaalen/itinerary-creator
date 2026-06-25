# VIPIN_FULL Vipin Excel Corpus Regression Report

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
- Rows under 80 confidence: 205
- Whole-corpus generation smoke: passed
- Bad-output log: `docs/reports/vipin_nordic_calculator_bad_outputs.jsonl`

## Bad-output counts

- missing_source_city: 381
- overlong_title: 173
- missing_source_date: 87
- missing_source_day: 85
- activity_text_used_as_title: 82
- non_itinerary_type: 65
- unexpected_skip: 35
- missing_source_type: 21
- missing_parsed_city: 9

## Parser review flags

- very_long_supplier_text: 324
- missing_hotel_name: 102
- missing_route_origin: 101
- missing_room_category: 87
- missing_route_destination: 87
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
- Vipin Calculator Nordic 2.xlsx:: 10 Pax 10085 v4 Group Tour ::R21 | type='Transfer' | title='Private transfer Fjellheisen cable car to the polar museum, søndre tollbodgate 11, 11, 90089008 Tromsø' | generated='Private transfer Fjellheisen cable car to the polar museum, søndre tollbodgate 11, 11, 90089008 Tromsø' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx:: 10085 v2 16 Pax  Group Tour ::R18 | type='Transfer' | title='Private transfer Fjellheisen cable car to the polar museum, søndre tollbodgate 11, 11, 90089008 Tromsø' | generated='Private transfer Fjellheisen cable car to the polar museum, søndre tollbodgate 11, 11, 90089008 Tromsø' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx:: 10162v2::R11 | type='Transfer' | title='bus: Long distance comfortable panorama coach transfer from Rovaniemi bus Station to Saariselkä - Tickets Included' | generated='bus: Long distance comfortable panorama coach transfer from Rovaniemi bus Station to Saariselkä - Tickets Included' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx:: 10162v2::R13 | type='Transfer' | title='bus: Long distance comfortable panorama coach transfer from Saariselkä t to Rovaniemi bus Station - Tickets Included' | generated='bus: Long distance comfortable panorama coach transfer from Saariselkä t to Rovaniemi bus Station - Tickets Included' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10066::R8 | type='Day overview' | title='Flight to the Golden Circle, South Coast, East Fjords, North Iceland, West Iceland, and the Snæfellsnes, including the Highlands at Landmannalaugar. Your journey begins with geysers, waterfalls, and black sand beaches, continues along dramatic coastlines, glaciers, ice caves, canyons, and lava fields, and concludes with Whale Watching, geothermal baths, volcanic craters, and the striking scenery of Snæfellsnes. Stay in comfortable hotels with breakfast included, and travel in a well-equipped minibus with an experienced guide. Transportation between destinations, guided activities, and accommodation are all included. Simply arrive in Reykjavík on your selected date and follow the itinerary. Book your return flight from Reykjavík after the tour ends on Day 8. This guided holiday is suitable for anyone in normal health and ready for light outdoor activities' | generated='Flight to the Golden Circle, South Coast, East Fjords, North Iceland, West Iceland, and the Snæfellsnes, including the Highlands at Landmannalaugar. Your journey begins with geysers, waterfalls, and black sand beaches, continues along dramatic coastlines, glaciers, ice caves, canyons, and lava fields, and concludes with Whale Watching, geothermal baths, volcanic craters, and the striking scenery of Snæfellsnes. Stay in comfortable hotels with breakfast included, and travel in a well-equipped minibus with an experienced guide. Transportation between destinations, guided activities, and accommodation are all included. Simply arrive in Reykjavík on your selected date and follow the itinerary. Book your return flight from Reykjavík after the tour ends on Day 8. This guided holiday is suitable for anyone in normal health and ready for light outdoor activities' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10066::R12 | type='Day overview' | title="Traverse North Iceland’s Waterfalls and Volcanic Landscapes After enjoying a delicious breakfast, it's time to hit the road again. Begin your day with a visit to Stuðlagil Canyon, known for its striking basalt columns and stunning blue glacial river. Explore this hidden gem and witness the unique formations that make it a photographer's paradise. Continuing your journey" | generated="Traverse North Iceland’s Waterfalls and Volcanic Landscapes After enjoying a delicious breakfast, it's time to hit the road again. Begin your day with a visit to Stuðlagil Canyon, known for its striking basalt columns and stunning blue glacial river. Explore this hidden gem and witness the unique formations that make it a photographer's paradise. Continuing your journey" | reason=Parsed title is over 100 characters.

### activity_text_used_as_title
- Vipin Calculator Nordic 2.xlsx::10066::R8 | type='Day overview' | title='Flight to the Golden Circle, South Coast, East Fjords, North Iceland, West Iceland, and the Snæfellsnes, including the Highlands at Landmannalaugar. Your journey begins with geysers, waterfalls, and black sand beaches, continues along dramatic coastlines, glaciers, ice caves, canyons, and lava fields, and concludes with Whale Watching, geothermal baths, volcanic craters, and the striking scenery of Snæfellsnes. Stay in comfortable hotels with breakfast included, and travel in a well-equipped minibus with an experienced guide. Transportation between destinations, guided activities, and accommodation are all included. Simply arrive in Reykjavík on your selected date and follow the itinerary. Book your return flight from Reykjavík after the tour ends on Day 8. This guided holiday is suitable for anyone in normal health and ready for light outdoor activities' | generated='Flight to the Golden Circle, South Coast, East Fjords, North Iceland, West Iceland, and the Snæfellsnes, including the Highlands at Landmannalaugar. Your journey begins with geysers, waterfalls, and black sand beaches, continues along dramatic coastlines, glaciers, ice caves, canyons, and lava fields, and concludes with Whale Watching, geothermal baths, volcanic craters, and the striking scenery of Snæfellsnes. Stay in comfortable hotels with breakfast included, and travel in a well-equipped minibus with an experienced guide. Transportation between destinations, guided activities, and accommodation are all included. Simply arrive in Reykjavík on your selected date and follow the itinerary. Book your return flight from Reykjavík after the tour ends on Day 8. This guided holiday is suitable for anyone in normal health and ready for light outdoor activities' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10066::R12 | type='Day overview' | title="Traverse North Iceland’s Waterfalls and Volcanic Landscapes After enjoying a delicious breakfast, it's time to hit the road again. Begin your day with a visit to Stuðlagil Canyon, known for its striking basalt columns and stunning blue glacial river. Explore this hidden gem and witness the unique formations that make it a photographer's paradise. Continuing your journey" | generated="Traverse North Iceland’s Waterfalls and Volcanic Landscapes After enjoying a delicious breakfast, it's time to hit the road again. Begin your day with a visit to Stuðlagil Canyon, known for its striking basalt columns and stunning blue glacial river. Explore this hidden gem and witness the unique formations that make it a photographer's paradise. Continuing your journey" | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10066::R13 | type='Day overview' | title='Experience Whale Watching and Coastal Heritage Start your day with a delicious breakfast before exploring the charming town of Akureyri, known as the "Capital of the North. " Take a leisurely walk to the harbor and embark on a thrilling Whale Watching Tour. Keep your eyes peeled for magnificent whales as they breach the surface of the ocean, creating unforgettable memories. After the whale-watching adventure, enjoy a leisurely lunch in Akureyri before continuing your journey. Drive to Glaumbær, a historic turf farm and open-air museum that offers a glimpse into Iceland\'s rural past. Step back in time as you explore the traditional turf houses and gain insight into the country\'s rich cultural heritage. Next, visit Borgarvirki, an ancient volcanic plug that served as a fortress in Iceland\'s Viking Age. Learn about its historical significance and enjoy panoramic views of the surrounding landscapes. Continue your journey to Hvítserkur, a striking rock formation rising from the sea. Marvel at the unique shape of this monolith and let your imagination run wild as you contemplate the mythical tales associated with it' | generated='Experience Whale Watching and Coastal Heritage Start your day with a delicious breakfast before exploring the charming town of Akureyri, known as the "Capital of the North. " Take a leisurely walk to the harbor and embark on a thrilling Whale Watching Tour. Keep your eyes peeled for magnificent whales as they breach the surface of the ocean, creating unforgettable memories. After the whale-watching adventure, enjoy a leisurely lunch in Akureyri before continuing your journey. Drive to Glaumbær, a historic turf farm and open-air museum that offers a glimpse into Iceland\'s rural past. Step back in time as you explore the traditional turf houses and gain insight into the country\'s rich cultural heritage. Next, visit Borgarvirki, an ancient volcanic plug that served as a fortress in Iceland\'s Viking Age. Learn about its historical significance and enjoy panoramic views of the surrounding landscapes. Continue your journey to Hvítserkur, a striking rock formation rising from the sea. Marvel at the unique shape of this monolith and let your imagination run wild as you contemplate the mythical tales associated with it' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10066::R14 | type='Day overview' | title='Climb Craters and Explore West Iceland’s Hot Springs On the final day of your Icelandic adventure, savor a delicious breakfast before continuing your journey' | generated='Climb Craters and Explore West Iceland’s Hot Springs On the final day of your Icelandic adventure, savor a delicious breakfast before continuing your journey' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10071::R7 | type='Activity' | title="Embark on an unforgettable journey through Iceland's breathtaking landscapes on the Ultimate Icelandic Adventure Tour. Your adventure begins with a pick-up in Reykjavík, followed by a scenic drive to Þingvellir National Park, a UNESCO World Heritage site. Immerse yourself in the historic and geological wonders of Þingvellir National Park, where you can explore the dramatic rift valley and learn about Iceland's fascinating history. Continuing the journey" | generated="Embark on an unforgettable journey through Iceland's breathtaking landscapes on the Ultimate Icelandic Adventure Tour. Your adventure begins with a pick-up in Reykjavík, followed by a scenic drive to Þingvellir National Park, a UNESCO World Heritage site. Immerse yourself in the historic and geological wonders of Þingvellir National Park, where you can explore the dramatic rift valley and learn about Iceland's fascinating history. Continuing the journey" | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10071::R10 | type='Activity' | title="After enjoying a delicious breakfast, it's time to hit the road again. Begin your day with a visit to Stuðlagil Canyon, known for its striking basalt columns and stunning blue glacial river. Explore this hidden gem and witness the unique formations that make it a photographer's paradise. Continuing your journey" | generated="After enjoying a delicious breakfast, it's time to hit the road again. Begin your day with a visit to Stuðlagil Canyon, known for its striking basalt columns and stunning blue glacial river. Explore this hidden gem and witness the unique formations that make it a photographer's paradise. Continuing your journey" | reason=Parsed title looks like supplier prose or activity body text.

### missing_parsed_city
- Vipin Calculator Nordic 2.xlsx::10102::R10 | type='Activity' | title='Helsinki Hop on Hop off 24 Hr ticket' | generated='Helsinki Hop on Hop off 24 Hr ticket' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10114::R42 | type='Transfer' | title='Departure' | generated='Departure' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10114v3::R51 | type='Transfer' | title='Departure' | generated='Departure' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10119::R10 | type='Activity' | title='Self Planned' | generated='Self Planned' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10126v2::R20 | type='Activity' | title='Leisure Day' | generated='Leisure Day' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10131::R10 | type='Transfer' | title='46206' | generated='46206' | reason=Parsed row is missing city/area.

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
