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
- Average parser confidence: 97.4%
- Rows under 80 confidence: 196
- Whole-corpus generation smoke: passed
- Bad-output log: `docs/reports/vipin_nordic_calculator_bad_outputs.jsonl`

## Bad-output counts

- missing_source_city: 381
- missing_source_date: 87
- overlong_title: 86
- missing_source_day: 85
- non_itinerary_type: 65
- activity_text_used_as_title: 63
- unexpected_skip: 35
- missing_source_type: 21
- missing_parsed_city: 8

## Parser review flags

- very_long_supplier_text: 324
- missing_route_origin: 101
- missing_hotel_name: 93
- missing_route_destination: 87
- missing_room_category: 80
- missing_city: 8
- weak_title: 6
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
- Vipin Calculator Nordic 2.xlsx::10066::R14 | type='Day overview' | title='Climb Craters and Explore West Iceland’s Hot Springs On the final day of your Icelandic adventure, savor a delicious breakfast before continuing your journey. Drive to Grábrók, a volcanic crater known for its stunning views and unique geological features. Take a short walk to the rim and soak in the panoramic vistas. Next, visit Glanni waterfall, a serene and picturesque cascade nestled in the beautiful Húsafell area. Enjoy the peaceful ambiance and let the sounds of nature soothe your soul. Continue your exploration to Hraunfossar, a series of cascading waterfalls flowing through lava fields, creating a mesmerizing sight. Marvel at the contrast between the vibrant blue water and the dark volcanic rocks. Afterward, visit Sturlureykir, a traditional Icelandic horse farm' | generated='Climb Craters and Explore West Iceland’s Hot Springs On the final day of your Icelandic adventure, savor a delicious breakfast before continuing your journey. Drive to Grábrók, a volcanic crater known for its stunning views and unique geological features. Take a short walk to the rim and soak in the panoramic vistas. Next, visit Glanni waterfall, a serene and picturesque cascade nestled in the beautiful Húsafell area. Enjoy the peaceful ambiance and let the sounds of nature soothe your soul. Continue your exploration to Hraunfossar, a series of cascading waterfalls flowing through lava fields, creating a mesmerizing sight. Marvel at the contrast between the vibrant blue water and the dark volcanic rocks. Afterward, visit Sturlureykir, a traditional Icelandic horse farm' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10071::R12 | type='Activity' | title='On the final day of your Icelandic adventure, savor a delicious breakfast before continuing your journey. Drive to Grábrók, a volcanic crater known for its stunning views and unique geological features. Take a short walk to the rim and soak in the panoramic vistas. Next, visit Glanni waterfall, a serene and picturesque cascade nestled in the beautiful Húsafell area. Enjoy the peaceful ambiance and let the sounds of nature soothe your soul. Continue your exploration to Hraunfossar, a series of cascading waterfalls flowing through lava fields, creating a mesmerizing sight. Marvel at the contrast between the vibrant blue water and the dark volcanic rocks. Afterward, visit Sturlureykir, a traditional Icelandic horse farm' | generated='On the final day of your Icelandic adventure, savor a delicious breakfast before continuing your journey. Drive to Grábrók, a volcanic crater known for its stunning views and unique geological features. Take a short walk to the rim and soak in the panoramic vistas. Next, visit Glanni waterfall, a serene and picturesque cascade nestled in the beautiful Húsafell area. Enjoy the peaceful ambiance and let the sounds of nature soothe your soul. Continue your exploration to Hraunfossar, a series of cascading waterfalls flowing through lava fields, creating a mesmerizing sight. Marvel at the contrast between the vibrant blue water and the dark volcanic rocks. Afterward, visit Sturlureykir, a traditional Icelandic horse farm' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10100v4::R9 | type='Transfer' | title='Train to Gothenburg: Direct train (10:13-13:42) incl. high-speed train and booked seats. Timing can vary slightly' | generated='Train to Gothenburg: Direct train (10:13-13:42) incl. high-speed train and booked seats. Timing can vary slightly' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10100v4::R14 | type='Transfer' | title='Train to Copenhagen: Direct train (09:55-13:28) incl. high-speed train and booked seats. Timing can vary slightly' | generated='Train to Copenhagen: Direct train (09:55-13:28) incl. high-speed train and booked seats. Timing can vary slightly' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10100v4::R17 | type='Transfer' | title='Self-transfer from hotel to cruise harbor by local taxi (the cheapest and most efficient way to travel)' | generated='Self-transfer from hotel to cruise harbor by local taxi (the cheapest and most efficient way to travel)' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10100v4::R19 | type='Transfer' | title='Self-transfer from cruise harbor to hotel by local taxi (the cheapest and most efficient way to travel)' | generated='Self-transfer from cruise harbor to hotel by local taxi (the cheapest and most efficient way to travel)' | reason=Parsed title is over 100 characters.

### activity_text_used_as_title
- Vipin Calculator Nordic 2.xlsx::10066::R14 | type='Day overview' | title='Climb Craters and Explore West Iceland’s Hot Springs On the final day of your Icelandic adventure, savor a delicious breakfast before continuing your journey. Drive to Grábrók, a volcanic crater known for its stunning views and unique geological features. Take a short walk to the rim and soak in the panoramic vistas. Next, visit Glanni waterfall, a serene and picturesque cascade nestled in the beautiful Húsafell area. Enjoy the peaceful ambiance and let the sounds of nature soothe your soul. Continue your exploration to Hraunfossar, a series of cascading waterfalls flowing through lava fields, creating a mesmerizing sight. Marvel at the contrast between the vibrant blue water and the dark volcanic rocks. Afterward, visit Sturlureykir, a traditional Icelandic horse farm' | generated='Climb Craters and Explore West Iceland’s Hot Springs On the final day of your Icelandic adventure, savor a delicious breakfast before continuing your journey. Drive to Grábrók, a volcanic crater known for its stunning views and unique geological features. Take a short walk to the rim and soak in the panoramic vistas. Next, visit Glanni waterfall, a serene and picturesque cascade nestled in the beautiful Húsafell area. Enjoy the peaceful ambiance and let the sounds of nature soothe your soul. Continue your exploration to Hraunfossar, a series of cascading waterfalls flowing through lava fields, creating a mesmerizing sight. Marvel at the contrast between the vibrant blue water and the dark volcanic rocks. Afterward, visit Sturlureykir, a traditional Icelandic horse farm' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10071::R12 | type='Activity' | title='On the final day of your Icelandic adventure, savor a delicious breakfast before continuing your journey. Drive to Grábrók, a volcanic crater known for its stunning views and unique geological features. Take a short walk to the rim and soak in the panoramic vistas. Next, visit Glanni waterfall, a serene and picturesque cascade nestled in the beautiful Húsafell area. Enjoy the peaceful ambiance and let the sounds of nature soothe your soul. Continue your exploration to Hraunfossar, a series of cascading waterfalls flowing through lava fields, creating a mesmerizing sight. Marvel at the contrast between the vibrant blue water and the dark volcanic rocks. Afterward, visit Sturlureykir, a traditional Icelandic horse farm' | generated='On the final day of your Icelandic adventure, savor a delicious breakfast before continuing your journey. Drive to Grábrók, a volcanic crater known for its stunning views and unique geological features. Take a short walk to the rim and soak in the panoramic vistas. Next, visit Glanni waterfall, a serene and picturesque cascade nestled in the beautiful Húsafell area. Enjoy the peaceful ambiance and let the sounds of nature soothe your soul. Continue your exploration to Hraunfossar, a series of cascading waterfalls flowing through lava fields, creating a mesmerizing sight. Marvel at the contrast between the vibrant blue water and the dark volcanic rocks. Afterward, visit Sturlureykir, a traditional Icelandic horse farm' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10093 Ref  1205::R19 | type='Transfer' | title='Self-arranged transfer to meeting point of Lyngen Stay ( Crystall lavvo )' | generated='Self-arranged transfer to meeting point of Lyngen Stay ( Crystall lavvo )' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10093v2::R17 | type='Transfer' | title='Self-arranged transfer to meeting point of Lyngen Stay ( Crystall lavvo )' | generated='Self-arranged transfer to meeting point of Lyngen Stay ( Crystall lavvo )' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10108::R7 | type='Notes' | title='This Day 2 Bergen to Bergen day toour can be upgraded to Fully English-speaking guided Version with Trip guide with additional cost of 75 EUR per persib' | generated='This Day 2 Bergen to Bergen day toour can be upgraded to Fully English-speaking guided Version with Trip guide with additional cost of 75 EUR per persib' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10115::R8 | type='Day overview' | title='Hike Waterfalls and Glacier Seljalandsfoss: the adventure begins with the powerful theatrics of Seljalandsfoss. Bring a raincoat and' | generated='Hike Waterfalls and Glacier Seljalandsfoss: the adventure begins with the powerful theatrics of Seljalandsfoss. Bring a raincoat and' | reason=Parsed title looks like supplier prose or activity body text.

### missing_parsed_city
- Vipin Calculator Nordic 2.xlsx::10114::R42 | type='Transfer' | title='Departure' | generated='Departure' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10114v3::R51 | type='Transfer' | title='Departure' | generated='Departure' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10119::R10 | type='Activity' | title='Self Planned' | generated='Self Planned' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10126v2::R20 | type='Activity' | title='Leisure Day' | generated='Leisure Day' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10131::R10 | type='Transfer' | title='46206' | generated='46206' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10150::R6 | type='Activity' | title='Group TOur' | generated='Group TOur' | reason=Parsed row is missing city/area.

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
