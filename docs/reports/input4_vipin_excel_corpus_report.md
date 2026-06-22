# INPUT4 Vipin Excel Corpus Regression Report

Purpose: run the real messy Nordic calculator corpus through parser and editable-title generation, then log risky outputs for regression hardening.

## Summary

- Corpus rows checked: 5557
- Parsed output rows: 5436
- Generated editable titles checked: 3034
- Workbooks: 2
- Sheets with extracted rows: 307
- Parser exceptions: 0
- Rows skipped by parser: 121
- Average parser confidence: 97.2%
- Rows under 80 confidence: 220
- Whole-corpus generation smoke: passed
- Bad-output log: `docs/reports/input4_vipin_excel_bad_outputs.jsonl`

## Bad-output counts

- missing_source_city: 381
- overlong_title: 306
- activity_text_used_as_title: 272
- missing_source_date: 87
- missing_source_day: 85
- non_itinerary_type: 65
- unexpected_skip: 38
- missing_source_type: 21
- missing_parsed_city: 19

## Parser review flags

- very_long_supplier_text: 324
- missing_route_origin: 116
- missing_hotel_name: 102
- missing_route_destination: 92
- missing_room_category: 88
- missing_city: 19
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
- notes: 9
- departure: 9
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
- Vipin Calculator Nordic 2.xlsx:: 10 Pax 10085 v4 Group Tour ::R8 | type='Activity' | title='Private Transfer Santa Claus Village to Hotel Pls note: Dag Sledding final timing can be changed at the time of booking, as booking for jan is not yet released,' | generated='Private Transfer Santa Claus Village to Hotel Pls note: Dag Sledding final timing can be changed at the time of booking, as booking for jan is not yet released,' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx:: 10 Pax 10085 v4 Group Tour ::R20 | type='Activity' | title='Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening. Journey up and down the mountain in about 5 minutes with Fjellheisen Cable Car' | generated='Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening. Journey up and down the mountain in about 5 minutes with Fjellheisen Cable Car' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx:: 10085 v2 16 Pax  Group Tour ::R6 | type='Activity' | title='Snowmobiling and Reindeer & Husky Sledding, Arctic Circle Highlights, with Free time in Santa Claus Village with Lunch' | generated='Snowmobiling and Reindeer & Husky Sledding, Arctic Circle Highlights, with Free time in Santa Claus Village with Lunch' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx:: 10085 v2 16 Pax  Group Tour ::R17 | type='Activity' | title='Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening. Journey up and down the mountain in about 5 minutes with Fjellheisen Cable Car' | generated='Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening. Journey up and down the mountain in about 5 minutes with Fjellheisen Cable Car' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10061::R6 | type='Day overview' | title='Arrive in Reykjavík Make your way to Reykjavík, and check into your accommodation in the afternoon. Free day in Reykjavík.' | generated='Arrive in Reykjavík Make your way to Reykjavík, and check into your accommodation in the afternoon. Free day in Reykjavík.' | reason=Parsed title is over 100 characters.
- Vipin Calculator Nordic 2.xlsx::10061::R7 | type='Day overview' | title="Explore the Golden Circle and South Coast The day starts with a pick-up from your accommodation in Reykjavík. First, we will head out to explore the famous Golden Circle, which includes Þingvellir National Park where Icelanders founded their parliament in the year 930 A. D. , the oldest parliament in the world. The Circle includes Geysir hot springs and Gullfoss. Next, we will drive to the beautiful South Coast. Our first stop is at Seljalandsfoss, a unique opportunity to experience the power and wonder of nature. Don't view this one from a distance" | generated="Explore the Golden Circle and South Coast The day starts with a pick-up from your accommodation in Reykjavík. First, we will head out to explore the famous Golden Circle, which includes Þingvellir National Park where Icelanders founded their parliament in the year 930 A. D. , the oldest parliament in the world. The Circle includes Geysir hot springs and Gullfoss. Next, we will drive to the beautiful South Coast. Our first stop is at Seljalandsfoss, a unique opportunity to experience the power and wonder of nature. Don't view this one from a distance" | reason=Parsed title is over 100 characters.

### activity_text_used_as_title
- Vipin Calculator Nordic 2.xlsx:: 10 Pax 10085 v4 Group Tour ::R20 | type='Activity' | title='Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening. Journey up and down the mountain in about 5 minutes with Fjellheisen Cable Car' | generated='Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening. Journey up and down the mountain in about 5 minutes with Fjellheisen Cable Car' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx:: 10085 v2 16 Pax  Group Tour ::R6 | type='Activity' | title='Snowmobiling and Reindeer & Husky Sledding, Arctic Circle Highlights, with Free time in Santa Claus Village with Lunch' | generated='Snowmobiling and Reindeer & Husky Sledding, Arctic Circle Highlights, with Free time in Santa Claus Village with Lunch' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx:: 10085 v2 16 Pax  Group Tour ::R17 | type='Activity' | title='Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening. Journey up and down the mountain in about 5 minutes with Fjellheisen Cable Car' | generated='Enjoy the spectacular view of Tromsø and its beautiful surroundings from above, daytime or evening. Journey up and down the mountain in about 5 minutes with Fjellheisen Cable Car' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10061::R6 | type='Day overview' | title='Arrive in Reykjavík Make your way to Reykjavík, and check into your accommodation in the afternoon. Free day in Reykjavík.' | generated='Arrive in Reykjavík Make your way to Reykjavík, and check into your accommodation in the afternoon. Free day in Reykjavík.' | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10061::R7 | type='Day overview' | title="Explore the Golden Circle and South Coast The day starts with a pick-up from your accommodation in Reykjavík. First, we will head out to explore the famous Golden Circle, which includes Þingvellir National Park where Icelanders founded their parliament in the year 930 A. D. , the oldest parliament in the world. The Circle includes Geysir hot springs and Gullfoss. Next, we will drive to the beautiful South Coast. Our first stop is at Seljalandsfoss, a unique opportunity to experience the power and wonder of nature. Don't view this one from a distance" | generated="Explore the Golden Circle and South Coast The day starts with a pick-up from your accommodation in Reykjavík. First, we will head out to explore the famous Golden Circle, which includes Þingvellir National Park where Icelanders founded their parliament in the year 930 A. D. , the oldest parliament in the world. The Circle includes Geysir hot springs and Gullfoss. Next, we will drive to the beautiful South Coast. Our first stop is at Seljalandsfoss, a unique opportunity to experience the power and wonder of nature. Don't view this one from a distance" | reason=Parsed title looks like supplier prose or activity body text.
- Vipin Calculator Nordic 2.xlsx::10061::R8 | type='Day overview' | title="Trek and Hike on the Glacier The journey continues along the South Coast in the direction of Skaftafell and Vatnajökull. At Skaftafell, another of Iceland's three national parks, we will take a 3-hour glacier hike on one of Vatnajökull outlet glaciers, led by one of our skilled glacier guides. After that bracing experience, we will explore a little further Jökulsárlón where we can expect to see floating icebergs and the occasional frolicking seal. Beside the glacier lake, we will find another black sand crystal beach, which is usually filled with clear icebergs that have floated back to shore. For the evening, we will lay our heads in accommodations in the pleasant seaside town of Höfn." | generated="Trek and Hike on the Glacier The journey continues along the South Coast in the direction of Skaftafell and Vatnajökull. At Skaftafell, another of Iceland's three national parks, we will take a 3-hour glacier hike on one of Vatnajökull outlet glaciers, led by one of our skilled glacier guides. After that bracing experience, we will explore a little further Jökulsárlón where we can expect to see floating icebergs and the occasional frolicking seal. Beside the glacier lake, we will find another black sand crystal beach, which is usually filled with clear icebergs that have floated back to shore. For the evening, we will lay our heads in accommodations in the pleasant seaside town of Höfn." | reason=Parsed title looks like supplier prose or activity body text.

### missing_parsed_city
- Vipin Calculator Nordic 2.xlsx::10060::R4 | type='Transfer' | title='Aarhus' | generated='Aarhus' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10085 Group Tour ::R9 | type='Activity' | title='Kiruna' | generated='Kiruna' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10085.1 TL cost Group Tour ::R9 | type='Activity' | title='Kiruna' | generated='Kiruna' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10085.2 12 pax ::R9 | type='Activity' | title='Kiruna' | generated='Kiruna' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10085.2 14 pax ::R9 | type='Activity' | title='Kiruna' | generated='Kiruna' | reason=Parsed row is missing city/area.
- Vipin Calculator Nordic 2.xlsx::10085.2 16 pax ::R9 | type='Activity' | title='Kiruna' | generated='Kiruna' | reason=Parsed row is missing city/area.

### unexpected_skip
- Vipin Nordic Calculator 3.xlsx::10240 ref 917::R13 | type='Transfer' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.
- Vipin Nordic Calculator 3.xlsx::10204::R14 | type='Transfer' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.
- Vipin Calculator Nordic 2.xlsx::New Template::R72 | type='Day 3' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.
- Vipin Calculator Nordic 2.xlsx::10175.1::R14 | type='Transfer' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.
- Vipin Calculator Nordic 2.xlsx::10175.2::R15 | type='Transfer' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.
- Vipin Calculator Nordic 2.xlsx::10155::R4 | type='Transfer' | title='' | generated='' | reason=Parser returned no row for this itinerary-like source row.

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
- Vipin Nordic Calculator 3.xlsx::10235::R4 | type='Day overview' | title='' | generated='' | reason=Source row has no city/area value.
- Vipin Nordic Calculator 3.xlsx::10235::R6 | type='Day overview' | title='' | generated='' | reason=Source row has no city/area value.
- Vipin Nordic Calculator 3.xlsx::10235::R7 | type='Day overview' | title='' | generated='' | reason=Source row has no city/area value.
- Vipin Nordic Calculator 3.xlsx::10235::R8 | type='Day overview' | title='' | generated='' | reason=Source row has no city/area value.
- Vipin Nordic Calculator 3.xlsx::10235::R9 | type='Day overview' | title='' | generated='' | reason=Source row has no city/area value.
- Vipin Nordic Calculator 3.xlsx::10235::R11 | type='Leisure' | title='' | generated='' | reason=Source row has no city/area value.

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
