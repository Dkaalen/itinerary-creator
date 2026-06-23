"""Structured Nordic destination registry built from the legacy place list.

The parser still depends on ``place_alias_data.PLACES``.  This module adds a
richer read model on top of that source so copy, image and route systems can
scale to hundreds of useful Nordic itinerary destinations without each feature
maintaining its own hardcoded city list.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable
import re
import unicodedata

from place_alias_data import PLACES


@dataclass(frozen=True)
class NordicDestination:
    name: str
    country: str
    region: str
    destination_type: str
    aliases: tuple[str, ...]
    nearby_hubs: tuple[str, ...]
    season_profile: str
    image_profile: str
    copy_profile: str
    transport_role: tuple[str, ...]
    priority: int


TRAVEL_DESTINATION_KINDS = frozenset({
    "city",
    "town",
    "village",
    "resort",
    "island",
    "region",
    "fjord",
    "national_park",
    "route",
})

ARCTIC_NORWAY = frozenset({
    "Alta",
    "Andenes",
    "Båtsfjord",
    "Bardufoss",
    "Berlevåg",
    "Finnsnes",
    "Hammerfest",
    "Harstad",
    "Havøysund",
    "Honningsvåg",
    "Karasjok",
    "Kautokeino",
    "Kirkenes",
    "Kjøllefjord",
    "Kvaløya",
    "Lakselv",
    "Longyearbyen",
    "Lyngen",
    "Mehamn",
    "Narvik",
    "North Cape",
    "Øksfjord",
    "Senja",
    "Setermoen",
    "Skjervøy",
    "Sommarøy",
    "Sortland",
    "Stokmarknes",
    "Storslett",
    "Svalbard",
    "Tana",
    "Tromsø",
    "Vadsø",
    "Vardø",
    "Varanger",
    "Vesterålen",
})

SOUTHERN_COASTAL_NORWAY = frozenset({
    "Arendal",
    "Bergen",
    "Bømlo",
    "Egersund",
    "Farsund",
    "Fedje",
    "Flekkefjord",
    "Florø",
    "Fredrikstad",
    "Grimstad",
    "Halden",
    "Haugesund",
    "Horten",
    "Kalvåg",
    "Kopervik",
    "Kragerø",
    "Kristiansand",
    "Larvik",
    "Lillesand",
    "Mandal",
    "Moss",
    "Måløy",
    "Oslo",
    "Porsgrunn",
    "Risør",
    "Sandefjord",
    "Sandnes",
    "Skudeneshavn",
    "Sola",
    "Stavanger",
    "Stord",
    "Tønsberg",
    "Utsira",
    "Ålesund",
})

ARCTIC_SWEDEN = frozenset({
    "Abisko",
    "Abisko National Park",
    "Ammarnäs",
    "Arjeplog",
    "Arvidsjaur",
    "Björkliden",
    "Boden",
    "Gällivare",
    "Haparanda",
    "Hemavan",
    "Jokkmokk",
    "Jukkasjärvi",
    "Kebnekaise",
    "Kiruna",
    "Kungsleden",
    "Laponia",
    "Luleå",
    "Padjelanta",
    "Piteå",
    "Riksgränsen",
    "Sarek",
    "Skellefteå",
    "Sorsele",
    "Stora Sjöfallet",
    "Swedish Icehotel Region",
    "Swedish Lapland",
    "Tärnaby",
})

SOUTHERN_COASTAL_SWEDEN = frozenset({
    "Falkenberg",
    "Falsterbo",
    "Fjällbacka",
    "Fårö",
    "Gothenburg",
    "Gotland",
    "Halmstad",
    "Helsingborg",
    "Kalmar",
    "Karlshamn",
    "Karlskrona",
    "Kivik",
    "Koster Islands",
    "Lysekil",
    "Malmö",
    "Marstrand",
    "Nynäshamn",
    "Sandhamn",
    "Simrishamn",
    "Smögen",
    "Stockholm",
    "Stockholm Archipelago",
    "Strömstad",
    "Trelleborg",
    "Utö",
    "Varberg",
    "Ven",
    "Visby",
    "Vaxholm",
    "Ystad",
    "Öland",
})

ARCTIC_FINLAND = frozenset({
    "Enontekiö",
    "Finnish Lapland",
    "Hetta",
    "Inari",
    "Ivalo",
    "Kakslauttanen",
    "Karigasniemi",
    "Kemi",
    "Kemijärvi",
    "Kiilopää",
    "Kilpisjärvi",
    "Kittilä",
    "Kolari",
    "Kuusamo",
    "Levi",
    "Lemmenjoki",
    "Lemmenjoki National Park",
    "Luosto",
    "Muonio",
    "Nellim",
    "Nuorgam",
    "Oulanka",
    "Pallas",
    "Pallas-Yllästunturi",
    "Posio",
    "Pyhä",
    "Pyhä-Luosto",
    "Ranua",
    "Rovaniemi",
    "Ruka",
    "Saariselkä",
    "Salla",
    "Savukoski",
    "Sevettijärvi",
    "Sodankylä",
    "Syöte",
    "Tankavaara",
    "Tornio",
    "Urho Kekkonen",
    "Utsjoki",
    "Ylläs",
    "Äkäslompolo",
})

SOUTHERN_COASTAL_FINLAND = frozenset({
    "Archipelago National Park",
    "Archipelago Sea",
    "Bengtskär",
    "Espoo",
    "Hamina",
    "Hanko",
    "Helsinki",
    "Inkoo",
    "Kimitoön",
    "Kökar",
    "Korpo",
    "Kotka",
    "Kvarken Archipelago",
    "Mariehamn",
    "Naantali",
    "Nagu",
    "Pargas",
    "Pori",
    "Porvoo",
    "Rauma",
    "Raseborg",
    "Salo",
    "Tammisaari",
    "Turku",
    "Uusikaupunki",
    "Utö",
    "Vaasa",
    "Åland",
})

NORWAY_REGION_OVERRIDES = {
    "Oslo": "Eastern Norway",
    "Lillestrøm": "Eastern Norway",
    "Eidsvoll": "Eastern Norway",
    "Hamar": "Eastern Norway",
    "Gjøvik": "Eastern Norway",
    "Kongsvinger": "Eastern Norway",
    "Moss": "Oslofjord",
    "Fredrikstad": "Oslofjord",
    "Sarpsborg": "Oslofjord",
    "Halden": "Oslofjord",
    "Horten": "Oslofjord",
    "Tønsberg": "Oslofjord",
    "Drammen": "Eastern Norway",
    "Larvik": "Vestfold and Telemark",
    "Sandefjord": "Vestfold and Telemark",
    "Porsgrunn": "Vestfold and Telemark",
    "Skien": "Vestfold and Telemark",
    "Notodden": "Vestfold and Telemark",
    "Rjukan": "Vestfold and Telemark",
    "Kragerø": "Southern Norway",
    "Risør": "Southern Norway",
    "Arendal": "Southern Norway",
    "Grimstad": "Southern Norway",
    "Lillesand": "Southern Norway",
    "Kristiansand": "Southern Norway",
    "Mandal": "Southern Norway",
    "Flekkefjord": "Southern Norway",
    "Farsund": "Southern Norway",
    "Lyngdal": "Southern Norway",
    "Setesdal": "Southern Norway",
    "Hovden": "Southern Norway",
    "Stavanger": "Rogaland",
    "Sandnes": "Rogaland",
    "Sola": "Rogaland",
    "Egersund": "Rogaland",
    "Haugesund": "Rogaland",
    "Kopervik": "Rogaland",
    "Skudeneshavn": "Rogaland",
    "Utsira": "Rogaland",
    "Ryfylke": "Rogaland",
    "Sauda": "Rogaland",
    "Jørpeland": "Rogaland",
    "Tau": "Rogaland",
    "Bergen": "Western Norway",
    "Flåm": "Sognefjord",
    "Myrdal": "Sognefjord",
    "Voss": "Western Norway",
    "Gudvangen": "Sognefjord",
    "Balestrand": "Sognefjord",
    "Lærdal": "Sognefjord",
    "Aurland": "Sognefjord",
    "Undredal": "Sognefjord",
    "Solvorn": "Sognefjord",
    "Kaupanger": "Sognefjord",
    "Odda": "Hardanger",
    "Eidfjord": "Hardanger",
    "Ulvik": "Hardanger",
    "Norheimsund": "Hardanger",
    "Rosendal": "Hardanger",
    "Loen": "Nordfjord",
    "Olden": "Nordfjord",
    "Stryn": "Nordfjord",
    "Nordfjordeid": "Nordfjord",
    "Førde": "Sunnfjord",
    "Florø": "Sunnfjord",
    "Måløy": "Nordfjord",
    "Kalvåg": "Western Norway",
    "Geiranger": "Geirangerfjord",
    "Ålesund": "Møre og Romsdal",
    "Åndalsnes": "Møre og Romsdal",
    "Molde": "Møre og Romsdal",
    "Kristiansund": "Møre og Romsdal",
    "Hellesylt": "Geirangerfjord",
    "Valldal": "Møre og Romsdal",
    "Trondheim": "Trøndelag",
    "Røros": "Trøndelag",
    "Oppdal": "Trøndelag",
    "Stjørdal": "Trøndelag",
    "Levanger": "Trøndelag",
    "Steinkjer": "Trøndelag",
    "Namsos": "Trøndelag",
    "Bodø": "Northern Norway",
    "Svolvær": "Lofoten",
    "Leknes": "Lofoten",
    "Reine": "Lofoten",
    "Hamnøy": "Lofoten",
    "Nusfjord": "Lofoten",
    "Henningsvær": "Lofoten",
    "Kabelvåg": "Lofoten",
    "Ballstad": "Lofoten",
    "Ramberg": "Lofoten",
    "Å i Lofoten": "Lofoten",
    "Narvik": "Northern Norway",
    "Tromsø": "Northern Norway",
    "Alta": "Northern Norway",
    "Kirkenes": "Northern Norway",
    "Longyearbyen": "Svalbard",
}

SWEDEN_REGION_OVERRIDES = {
    "Stockholm": "Stockholm and Central Sweden",
    "Uppsala": "Stockholm and Central Sweden",
    "Sigtuna": "Stockholm and Central Sweden",
    "Mariefred": "Stockholm and Central Sweden",
    "Trosa": "Stockholm and Central Sweden",
    "Nyköping": "Stockholm and Central Sweden",
    "Nynäshamn": "Stockholm Archipelago",
    "Vaxholm": "Stockholm Archipelago",
    "Sandhamn": "Stockholm Archipelago",
    "Grinda": "Stockholm Archipelago",
    "Utö": "Stockholm Archipelago",
    "Gothenburg": "West Sweden",
    "Marstrand": "West Sweden",
    "Lysekil": "West Sweden",
    "Fjällbacka": "West Sweden",
    "Smögen": "West Sweden",
    "Strömstad": "West Sweden",
    "Koster Islands": "West Sweden",
    "Trollhättan": "West Sweden",
    "Vänersborg": "West Sweden",
    "Lidköping": "West Sweden",
    "Skövde": "West Sweden",
    "Malmö": "Skåne",
    "Lund": "Skåne",
    "Helsingborg": "Skåne",
    "Ystad": "Skåne",
    "Simrishamn": "Skåne",
    "Kristianstad": "Skåne",
    "Trelleborg": "Skåne",
    "Falsterbo": "Skåne",
    "Kivik": "Skåne",
    "Båstad": "Skåne",
    "Ängelholm": "Skåne",
    "Söderåsen": "Skåne",
    "Ven": "Skåne",
    "Kalmar": "Småland and Islands",
    "Karlskrona": "Småland and Islands",
    "Karlshamn": "Småland and Islands",
    "Växjö": "Småland and Islands",
    "Jönköping": "Småland and Islands",
    "Gränna": "Småland and Islands",
    "Eksjö": "Småland and Islands",
    "Vimmerby": "Småland and Islands",
    "Gotland": "Gotland and Öland",
    "Visby": "Gotland and Öland",
    "Fårö": "Gotland and Öland",
    "Öland": "Gotland and Öland",
    "Dalarna": "Dalarna",
    "Falun": "Dalarna",
    "Borlänge": "Dalarna",
    "Tällberg": "Dalarna",
    "Mora": "Dalarna",
    "Rättvik": "Dalarna",
    "Leksand": "Dalarna",
    "Siljan": "Dalarna",
    "Sälen": "Dalarna",
    "Idre": "Dalarna",
    "Karlstad": "Värmland",
    "Västerås": "Central Sweden",
    "Örebro": "Central Sweden",
    "Linköping": "Östergötland",
    "Norrköping": "Östergötland",
    "Vadstena": "Östergötland",
    "Gävle": "Gävleborg",
    "Söderhamn": "Gävleborg",
    "Hudiksvall": "Gävleborg",
    "Sundsvall": "High Coast",
    "Härnösand": "High Coast",
    "Örnsköldsvik": "High Coast",
    "Höga Kusten": "High Coast",
    "Östersund": "Jämtland Härjedalen",
    "Åre": "Jämtland Härjedalen",
    "Duved": "Jämtland Härjedalen",
    "Vemdalen": "Jämtland Härjedalen",
    "Funäsdalen": "Jämtland Härjedalen",
    "Swedish Lapland": "Swedish Lapland",
    "Kiruna": "Swedish Lapland",
    "Abisko": "Swedish Lapland",
    "Abisko National Park": "Swedish Lapland",
    "Jukkasjärvi": "Swedish Lapland",
    "Swedish Icehotel Region": "Swedish Lapland",
    "Gällivare": "Swedish Lapland",
    "Jokkmokk": "Swedish Lapland",
    "Luleå": "Swedish Lapland",
    "Boden": "Swedish Lapland",
    "Haparanda": "Swedish Lapland",
    "Piteå": "Swedish Lapland",
    "Skellefteå": "Swedish Lapland",
    "Arvidsjaur": "Swedish Lapland",
    "Arjeplog": "Swedish Lapland",
    "Sorsele": "Swedish Lapland",
    "Ammarnäs": "Swedish Lapland",
    "Hemavan": "Swedish Lapland",
    "Tärnaby": "Swedish Lapland",
    "Riksgränsen": "Swedish Lapland",
    "Björkliden": "Swedish Lapland",
    "Kebnekaise": "Swedish Lapland",
    "Kungsleden": "Swedish Lapland",
    "Laponia": "Swedish Lapland",
    "Sarek": "Swedish Lapland",
    "Padjelanta": "Swedish Lapland",
    "Stora Sjöfallet": "Swedish Lapland",
}

FINLAND_REGION_OVERRIDES = {
    "Helsinki": "Capital Region",
    "Espoo": "Capital Region",
    "Vantaa": "Capital Region",
    "Kauniainen": "Capital Region",
    "Kerava": "Capital Region",
    "Järvenpää": "Capital Region",
    "Hyvinkää": "Capital Region",
    "Porvoo": "Southern Coast",
    "Lohja": "Southern Coast",
    "Raseborg": "Southern Coast",
    "Tammisaari": "Southern Coast",
    "Hanko": "Southern Coast",
    "Fiskars": "Southern Coast",
    "Inkoo": "Southern Coast",
    "Kotka": "Southern Coast",
    "Hamina": "Southern Coast",
    "Kouvola": "Southern Finland",
    "Hämeenlinna": "Southern Finland",
    "Riihimäki": "Southern Finland",
    "Forssa": "Southern Finland",
    "Lahti": "Southern Finland",
    "Tampere": "Western Lakeland",
    "Orivesi": "Western Lakeland",
    "Ylöjärvi": "Western Lakeland",
    "Kangasala": "Western Lakeland",
    "Turku": "Southwest Finland",
    "Naantali": "Southwest Finland",
    "Salo": "Southwest Finland",
    "Uusikaupunki": "Southwest Finland",
    "Pori": "West Coast",
    "Rauma": "West Coast",
    "Vaasa": "West Coast",
    "Kokkola": "West Coast",
    "Pietarsaari": "West Coast",
    "Seinäjoki": "Ostrobothnia",
    "Åland": "Åland and Archipelago",
    "Mariehamn": "Åland and Archipelago",
    "Pargas": "Åland and Archipelago",
    "Nagu": "Åland and Archipelago",
    "Korpo": "Åland and Archipelago",
    "Kimitoön": "Åland and Archipelago",
    "Kökar": "Åland and Archipelago",
    "Utö": "Åland and Archipelago",
    "Bengtskär": "Åland and Archipelago",
    "Archipelago Sea": "Åland and Archipelago",
    "Archipelago National Park": "Åland and Archipelago",
    "Kvarken Archipelago": "West Coast",
    "Hailuoto": "West Coast",
    "Finnish Lakeland": "Finnish Lakeland",
    "Jyväskylä": "Finnish Lakeland",
    "Jämsä": "Finnish Lakeland",
    "Mänttä-Vilppula": "Finnish Lakeland",
    "Kuopio": "Finnish Lakeland",
    "Savonlinna": "Finnish Lakeland",
    "Mikkeli": "Finnish Lakeland",
    "Lappeenranta": "Finnish Lakeland",
    "Imatra": "Finnish Lakeland",
    "Joensuu": "North Karelia",
    "Koli": "North Karelia",
    "Koli National Park": "North Karelia",
    "Nurmes": "North Karelia",
    "Lieksa": "North Karelia",
    "Punkaharju": "Finnish Lakeland",
    "Varkaus": "Finnish Lakeland",
    "Iisalmi": "Finnish Lakeland",
    "Linnansaari": "Finnish Lakeland",
    "Repovesi": "Southern Finland",
    "Nuuksio": "Capital Region",
    "Sipoonkorpi": "Capital Region",
    "Helvetinjärvi": "Western Lakeland",
    "Leivonmäki": "Finnish Lakeland",
    "Salamajärvi": "Ostrobothnia",
    "Oulu": "Northern Ostrobothnia",
    "Kajaani": "Kainuu",
    "Vuokatti": "Kainuu",
    "Tahko": "Finnish Lakeland",
    "Himos": "Finnish Lakeland",
    "Messilä": "Southern Finland",
    "Finnish Lapland": "Finnish Lapland",
    "Rovaniemi": "Finnish Lapland",
    "Kemi": "Finnish Lapland",
    "Tornio": "Finnish Lapland",
    "Kemijärvi": "Finnish Lapland",
    "Sodankylä": "Finnish Lapland",
    "Muonio": "Finnish Lapland",
    "Enontekiö": "Finnish Lapland",
    "Kilpisjärvi": "Finnish Lapland",
    "Hetta": "Finnish Lapland",
    "Kolari": "Finnish Lapland",
    "Äkäslompolo": "Finnish Lapland",
    "Pallas": "Finnish Lapland",
    "Pallas-Yllästunturi": "Finnish Lapland",
    "Levi": "Finnish Lapland",
    "Kittilä": "Finnish Lapland",
    "Ylläs": "Finnish Lapland",
    "Pyhä": "Finnish Lapland",
    "Luosto": "Finnish Lapland",
    "Salla": "Finnish Lapland",
    "Posio": "Finnish Lapland",
    "Savukoski": "Finnish Lapland",
    "Tankavaara": "Finnish Lapland",
    "Utsjoki": "Finnish Lapland",
    "Nuorgam": "Finnish Lapland",
    "Karigasniemi": "Finnish Lapland",
    "Ivalo": "Finnish Lapland",
    "Inari": "Finnish Lapland",
    "Nellim": "Finnish Lapland",
    "Sevettijärvi": "Finnish Lapland",
    "Saariselkä": "Finnish Lapland",
    "Kakslauttanen": "Finnish Lapland",
    "Lemmenjoki": "Finnish Lapland",
    "Lemmenjoki National Park": "Finnish Lapland",
    "Kiilopää": "Finnish Lapland",
    "Ruka": "Northern Ostrobothnia",
    "Kuusamo": "Northern Ostrobothnia",
    "Oulanka": "Northern Ostrobothnia",
    "Syöte": "Northern Ostrobothnia",
    "Iso-Syöte": "Northern Ostrobothnia",
    "Hossa": "Kainuu",
    "Urho Kekkonen": "Finnish Lapland",
    "Pyhä-Luosto": "Finnish Lapland",
}


SOUTHERN_COASTAL_DENMARK = frozenset({
    "Aabenraa",
    "Aalborg",
    "Aarhus",
    "Allinge",
    "Anholt",
    "Assens",
    "Blokhus",
    "Bornholm",
    "Christiansø",
    "Copenhagen",
    "Dragør",
    "Ebeltoft",
    "Esbjerg",
    "Faaborg",
    "Falster",
    "Fanø",
    "Fredericia",
    "Frederikshavn",
    "Funen",
    "Grenaa",
    "Gudhjem",
    "Haderslev",
    "Hanstholm",
    "Helsingør",
    "Hirtshals",
    "Hvide Sande",
    "Kalundborg",
    "Kerteminde",
    "Køge",
    "Langeland",
    "Læsø",
    "Lolland",
    "Løgstør",
    "Løkken",
    "Mandø",
    "Maribo",
    "Middelfart",
    "Møn",
    "Nakskov",
    "Nexø",
    "North Zealand",
    "Nykøbing Falster",
    "Odense",
    "Ribe",
    "Ringkøbing",
    "Rømø",
    "Rødby",
    "Rønne",
    "Samsø",
    "Skagen",
    "Svaneke",
    "Svendborg",
    "Sæby",
    "Sønderborg",
    "Thyborøn",
    "Tønder",
    "Vejle",
    "Wadden Sea National Park",
    "Zealand",
    "Ærø",
    "Ærøskøbing",
})


DENMARK_REGION_OVERRIDES = {
    "Copenhagen": "Greater Copenhagen",
    "Frederiksberg": "Greater Copenhagen",
    "Dragør": "Greater Copenhagen",
    "Copenhagen Airport": "Greater Copenhagen",
    "North Zealand": "North Zealand",
    "Helsingør": "North Zealand",
    "Kongernes Nordsjælland": "North Zealand",
    "Zealand": "Zealand",
    "Roskilde": "Zealand",
    "Køge": "Zealand",
    "Næstved": "Zealand",
    "Slagelse": "Zealand",
    "Kalundborg": "Zealand",
    "Holbæk": "Zealand",
    "Ringsted": "Zealand",
    "Sorø": "Zealand",
    "Stevns": "Zealand",
    "Stevns Klint": "Zealand",
    "Møn": "South Zealand and Islands",
    "Møns Klint": "South Zealand and Islands",
    "Lolland": "South Zealand and Islands",
    "Falster": "South Zealand and Islands",
    "Nykøbing Falster": "South Zealand and Islands",
    "Maribo": "South Zealand and Islands",
    "Nakskov": "South Zealand and Islands",
    "Rødby": "South Zealand and Islands",
    "Bornholm": "Bornholm",
    "Rønne": "Bornholm",
    "Svaneke": "Bornholm",
    "Gudhjem": "Bornholm",
    "Allinge": "Bornholm",
    "Nexø": "Bornholm",
    "Christiansø": "Bornholm",
    "Funen": "Funen and Islands",
    "Odense": "Funen and Islands",
    "Langeland": "Funen and Islands",
    "Ærø": "Funen and Islands",
    "Ærøskøbing": "Funen and Islands",
    "Svendborg": "Funen and Islands",
    "Faaborg": "Funen and Islands",
    "Middelfart": "Funen and Islands",
    "Nyborg": "Funen and Islands",
    "Bogense": "Funen and Islands",
    "Assens": "Funen and Islands",
    "Kerteminde": "Funen and Islands",
    "Jutland": "Jutland",
    "Aarhus": "East Jutland",
    "Aarhus Airport": "East Jutland",
    "Randers": "East Jutland",
    "Viborg": "East Jutland",
    "Horsens": "East Jutland",
    "Silkeborg": "East Jutland",
    "Ry": "East Jutland",
    "Skanderborg": "East Jutland",
    "Ebeltoft": "East Jutland",
    "Grenaa": "East Jutland",
    "Djursland": "East Jutland",
    "Mols Bjerge": "East Jutland",
    "Kolding": "South Jutland",
    "Vejle": "South Jutland",
    "Billund": "South Jutland",
    "Billund Airport": "South Jutland",
    "Fredericia": "South Jutland",
    "Sønderborg": "South Jutland",
    "Aabenraa": "South Jutland",
    "Haderslev": "South Jutland",
    "Tønder": "South Jutland",
    "Ribe": "South Jutland",
    "Esbjerg": "West Jutland",
    "Fanø": "West Jutland",
    "Mandø": "West Jutland",
    "Rømø": "West Jutland",
    "Wadden Sea National Park": "West Jutland",
    "Herning": "West Jutland",
    "Ikast": "West Jutland",
    "Holstebro": "West Jutland",
    "Ringkøbing": "West Jutland",
    "Hvide Sande": "West Jutland",
    "Søndervig": "West Jutland",
    "Lemvig": "West Jutland",
    "Struer": "West Jutland",
    "Aalborg": "North Jutland",
    "Aalborg Airport": "North Jutland",
    "Frederikshavn": "North Jutland",
    "Sæby": "North Jutland",
    "Hirtshals": "North Jutland",
    "Skagen": "North Jutland",
    "Løkken": "North Jutland",
    "Blokhus": "North Jutland",
    "Lønstrup": "North Jutland",
    "Hanstholm": "North Jutland",
    "Thisted": "North Jutland",
    "Thy": "North Jutland",
    "National Park Thy": "North Jutland",
    "Mors": "North Jutland",
    "Nykøbing Mors": "North Jutland",
    "Løgstør": "North Jutland",
    "Hobro": "North Jutland",
    "Mariager": "North Jutland",
    "Rebild": "North Jutland",
    "Anholt": "Danish Islands",
    "Læsø": "Danish Islands",
    "Samsø": "Danish Islands",
}

ICELAND_REGION_OVERRIDES = {
    "Reykjavík": "Capital Region",
    "Capital Region": "Capital Region",
    "Kópavogur": "Capital Region",
    "Hafnarfjörður": "Capital Region",
    "Garðabær": "Capital Region",
    "Mosfellsbær": "Capital Region",
    "Reykjavík Airport": "Capital Region",
    "Keflavík": "Reykjanes",
    "Keflavík Airport": "Reykjanes",
    "Reykjanes Peninsula": "Reykjanes",
    "Grindavík": "Reykjanes",
    "Garður": "Reykjanes",
    "Sandgerði": "Reykjanes",
    "Vogar": "Reykjanes",
    "Krýsuvík": "Reykjanes",
    "Fagradalsfjall": "Reykjanes",
    "Gunnuhver": "Reykjanes",
    "Kleifarvatn": "Reykjanes",
    "Blue Lagoon": "Reykjanes",
    "Sky Lagoon": "Capital Region",
    "Golden Circle": "Golden Circle",
    "Þingvellir National Park": "Golden Circle",
    "Geysir": "Golden Circle",
    "Gullfoss": "Golden Circle",
    "Kerið": "Golden Circle",
    "Hveragerði": "Golden Circle",
    "Laugarvatn": "Golden Circle",
    "Flúðir": "Golden Circle",
    "Skálholt": "Golden Circle",
    "Selfoss": "South Iceland",
    "Hella": "South Iceland",
    "Hvolsvöllur": "South Iceland",
    "Þjórsárdalur": "South Iceland",
    "Þórsmörk": "South Iceland",
    "Vestmannaeyjar": "South Coast and Islands",
    "Heimaey": "South Coast and Islands",
    "South Coast": "South Coast and Islands",
    "Vík": "South Coast and Islands",
    "Dyrhólaey": "South Coast and Islands",
    "Reynisfjara": "South Coast and Islands",
    "Skógafoss": "South Coast and Islands",
    "Seljalandsfoss": "South Coast and Islands",
    "Þakgil": "South Coast and Islands",
    "Kirkjubæjarklaustur": "South Coast and Islands",
    "Fjaðrárgljúfur": "South Coast and Islands",
    "Eldhraun": "South Coast and Islands",
    "Skaftafell": "Vatnajökull Region",
    "Vatnajökull": "Vatnajökull Region",
    "Jökulsárlón": "Vatnajökull Region",
    "Diamond Beach": "Vatnajökull Region",
    "Öræfi": "Vatnajökull Region",
    "Höfn": "Southeast Iceland",
    "Akranes": "West Iceland",
    "Borgarnes": "West Iceland",
    "Húsafell": "West Iceland",
    "Reykholt": "West Iceland",
    "Hraunfossar": "West Iceland",
    "Barnafoss": "West Iceland",
    "Deildartunguhver": "West Iceland",
    "Snæfellsnes": "Snæfellsnes",
    "Arnarstapi": "Snæfellsnes",
    "Hellnar": "Snæfellsnes",
    "Búðir": "Snæfellsnes",
    "Grundarfjörður": "Snæfellsnes",
    "Ólafsvík": "Snæfellsnes",
    "Hellissandur": "Snæfellsnes",
    "Kirkjufell": "Snæfellsnes",
    "Snæfellsjökull": "Snæfellsnes",
    "Stykkishólmur": "Snæfellsnes",
    "Westfjords": "Westfjords",
    "Ísafjörður": "Westfjords",
    "Ísafjörður Airport": "Westfjords",
    "Patreksfjörður": "Westfjords",
    "Bíldudalur": "Westfjords",
    "Tálknafjörður": "Westfjords",
    "Þingeyri": "Westfjords",
    "Flateyri": "Westfjords",
    "Súðavík": "Westfjords",
    "Hólmavík": "Westfjords",
    "Drangsnes": "Westfjords",
    "Dynjandi": "Westfjords",
    "Látrabjarg": "Westfjords",
    "Rauðasandur": "Westfjords",
    "Flatey": "Westfjords",
    "Hornstrandir": "Westfjords",
    "Akureyri": "North Iceland",
    "Akureyri Airport": "North Iceland",
    "Siglufjörður": "North Iceland",
    "Dalvík": "North Iceland",
    "Ólafsfjörður": "North Iceland",
    "Sauðárkrókur": "North Iceland",
    "Hofsós": "North Iceland",
    "Blönduós": "North Iceland",
    "Hvammstangi": "North Iceland",
    "Húsavík": "North Iceland",
    "Mývatn": "North Iceland",
    "Reykjahlíð": "North Iceland",
    "Skútustaðir": "North Iceland",
    "Dimmuborgir": "North Iceland",
    "Krafla": "North Iceland",
    "Ásbyrgi": "North Iceland",
    "Jökulsárgljúfur": "North Iceland",
    "Dettifoss": "North Iceland",
    "Goðafoss": "North Iceland",
    "Grímsey": "North Iceland",
    "Egilsstaðir": "East Iceland",
    "Egilsstaðir Airport": "East Iceland",
    "Seyðisfjörður": "East Iceland",
    "Eskifjörður": "East Iceland",
    "Neskaupstaður": "East Iceland",
    "Reyðarfjörður": "East Iceland",
    "Fáskrúðsfjörður": "East Iceland",
    "Stöðvarfjörður": "East Iceland",
    "Djúpivogur": "East Iceland",
    "Borgarfjörður Eystri": "East Iceland",
    "Vopnafjörður": "East Iceland",
    "Hallormsstaður": "East Iceland",
    "Hengifoss": "East Iceland",
    "Stuðlagil": "East Iceland",
    "Landmannalaugar": "Icelandic Highlands",
    "Icelandic Highlands": "Icelandic Highlands",
    "Kerlingarfjöll": "Icelandic Highlands",
    "Hveravellir": "Icelandic Highlands",
    "Askja": "Icelandic Highlands",
    "Lakagígar": "Icelandic Highlands",
    "Kjölur": "Icelandic Highlands",
    "Sprengisandur": "Icelandic Highlands",
    "Ring Road": "Iceland Ring Road",
}

REGION_FALLBACKS = {
    "Norway": "Norway",
    "Sweden": "Sweden",
    "Finland": "Finland",
    "Denmark": "Denmark",
    "Iceland": "Iceland",
}

RAIL_HUBS = frozenset({
    "Oslo",
    "Bergen",
    "Trondheim",
    "Kristiansand",
    "Stavanger",
    "Flåm",
    "Myrdal",
    "Voss",
    "Finse",
    "Geilo",
    "Gol",
    "Dombås",
    "Åndalsnes",
    "Bodø",
    "Narvik",
    "Stockholm",
    "Gothenburg",
    "Malmö",
    "Uppsala",
    "Linköping",
    "Norrköping",
    "Västerås",
    "Örebro",
    "Karlstad",
    "Gävle",
    "Sundsvall",
    "Östersund",
    "Åre",
    "Duved",
    "Umeå",
    "Luleå",
    "Boden",
    "Gällivare",
    "Kiruna",
    "Abisko",
    "Riksgränsen",
    "Helsinki",
    "Turku",
    "Tampere",
    "Oulu",
    "Rovaniemi",
    "Lahti",
    "Jyväskylä",
    "Kuopio",
    "Vaasa",
    "Pori",
    "Seinäjoki",
    "Kokkola",
    "Kouvola",
    "Lappeenranta",
    "Imatra",
    "Joensuu",
    "Kajaani",
    "Hämeenlinna",
    "Riihimäki",
    "Mikkeli",
    "Varkaus",
    "Iisalmi",
    "Kemi",
    "Tornio",
    "Kemijärvi",
    "Kolari",
    "Copenhagen",
    "Roskilde",
    "Odense",
    "Nyborg",
    "Middelfart",
    "Fredericia",
    "Kolding",
    "Vejle",
    "Horsens",
    "Aarhus",
    "Randers",
    "Aalborg",
    "Esbjerg",
    "Herning",
    "Viborg",
    "Silkeborg",
})

CRUISE_PORTS = frozenset({
    "Oslo",
    "Kristiansand",
    "Stavanger",
    "Bergen",
    "Flåm",
    "Geiranger",
    "Olden",
    "Loen",
    "Ålesund",
    "Molde",
    "Kristiansund",
    "Trondheim",
    "Bodø",
    "Svolvær",
    "Tromsø",
    "Alta",
    "Honningsvåg",
    "Kirkenes",
    "Stockholm",
    "Gothenburg",
    "Malmö",
    "Helsingborg",
    "Visby",
    "Kalmar",
    "Karlskrona",
    "Nynäshamn",
    "Strömstad",
    "Helsinki",
    "Turku",
    "Mariehamn",
    "Kotka",
    "Hanko",
    "Kemi",
    "Vaasa",
    "Copenhagen",
    "Aarhus",
    "Aalborg",
    "Fredericia",
    "Skagen",
    "Rønne",
    "Helsingør",
    "Esbjerg",
    "Hirtshals",
    "Frederikshavn",
    "Sønderborg",
    "Kolding",
    "Reykjavík",
    "Hafnarfjörður",
    "Keflavík",
    "Akureyri",
    "Húsavík",
    "Ísafjörður",
    "Stykkishólmur",
    "Grundarfjörður",
    "Seyðisfjörður",
    "Eskifjörður",
    "Djúpivogur",
    "Heimaey",
})

AIR_HUB_NAMES = frozenset({place["canonical"] for place in PLACES if place.get("kind") == "airport"})


def _aliases(place: dict) -> tuple[str, ...]:
    return tuple(str(alias).strip() for alias in place.get("aliases", ()) if str(alias).strip())


def _region(place: dict) -> str:
    name = str(place.get("canonical", ""))
    country = str(place.get("country", ""))
    if country == "Norway":
        return NORWAY_REGION_OVERRIDES.get(name, REGION_FALLBACKS.get(country, country))
    if country == "Sweden":
        return SWEDEN_REGION_OVERRIDES.get(name, REGION_FALLBACKS.get(country, country))
    if country == "Finland":
        return FINLAND_REGION_OVERRIDES.get(name, REGION_FALLBACKS.get(country, country))
    if country == "Denmark":
        return DENMARK_REGION_OVERRIDES.get(name, REGION_FALLBACKS.get(country, country))
    if country == "Iceland":
        return ICELAND_REGION_OVERRIDES.get(name, REGION_FALLBACKS.get(country, country))
    return REGION_FALLBACKS.get(country, country)


def _season_profile(place: dict) -> str:
    name = str(place.get("canonical", ""))
    country = str(place.get("country", ""))
    kind = str(place.get("kind", ""))
    if country == "Norway" and name in ARCTIC_NORWAY:
        return "arctic"
    if country == "Sweden" and name in ARCTIC_SWEDEN:
        return "arctic"
    if country == "Finland" and name in ARCTIC_FINLAND:
        return "arctic"
    if country == "Norway" and name in SOUTHERN_COASTAL_NORWAY:
        return "southern_coastal"
    if country == "Sweden" and name in SOUTHERN_COASTAL_SWEDEN:
        return "southern_coastal"
    if country == "Finland" and name in SOUTHERN_COASTAL_FINLAND:
        return "southern_coastal"
    if country == "Denmark" and name in SOUTHERN_COASTAL_DENMARK:
        return "southern_coastal"
    if country == "Iceland":
        region = ICELAND_REGION_OVERRIDES.get(name, "Iceland")
        if region == "Icelandic Highlands":
            return "iceland_highland"
        if region in {"North Iceland", "Westfjords", "East Iceland", "Southeast Iceland", "Vatnajökull Region"}:
            return "iceland_scenic"
        return "iceland_all_season"
    if kind in {"resort", "national_park"}:
        return "mountain"
    if kind in {"fjord", "island"}:
        return "coastal_nature"
    return "standard_nordic"


def _image_profile(place: dict) -> str:
    name = str(place.get("canonical", ""))
    country = str(place.get("country", ""))
    kind = str(place.get("kind", ""))
    if country == "Iceland":
        region = ICELAND_REGION_OVERRIDES.get(name, "Iceland")
        if kind == "route":
            return "iceland_route"
        if name in {"Blue Lagoon", "Sky Lagoon"}:
            return "thermal_lagoon"
        if region == "Icelandic Highlands":
            return "iceland_highland"
        if kind == "national_park":
            return "iceland_national_park"
        if kind in {"waterfall", "beach", "lagoon", "lake", "attraction"}:
            return "iceland_landmark"
        if name in CRUISE_PORTS:
            return "cruise_port"
        return "iceland_destination"
    if name in SOUTHERN_COASTAL_NORWAY or name in SOUTHERN_COASTAL_SWEDEN or name in SOUTHERN_COASTAL_FINLAND or name in SOUTHERN_COASTAL_DENMARK:
        return "southern_coastal"
    if name in ARCTIC_NORWAY or name in ARCTIC_SWEDEN or name in ARCTIC_FINLAND:
        return "arctic"
    if kind == "fjord":
        return "fjord"
    if kind == "island":
        return "island_coastal"
    if kind == "national_park":
        return "national_park"
    if kind == "resort":
        return "mountain_resort"
    if name in CRUISE_PORTS:
        return "cruise_port"
    if name in RAIL_HUBS:
        return "rail_hub"
    return kind or "destination"


def _copy_profile(place: dict) -> str:
    kind = str(place.get("kind", ""))
    country = str(place.get("country", ""))
    image_profile = _image_profile(place)
    if country == "Iceland":
        if image_profile in {"thermal_lagoon"}:
            return "thermal_lagoon"
        if kind == "route":
            return "scenic_route"
        if kind in {"national_park", "region", "fjord", "island"}:
            return "icelandic_nature"
        if kind in {"city", "town", "village"}:
            return "icelandic_town"
        return "icelandic_landmark"
    if image_profile in {"southern_coastal", "cruise_port"}:
        return "coastal_city"
    if image_profile == "arctic":
        return "arctic"
    if kind in {"fjord", "village"}:
        return "scenic_nature"
    if kind == "resort":
        return "mountain_resort"
    if kind == "national_park":
        return "national_park"
    if kind == "route":
        return "scenic_route"
    return "urban_culture" if kind in {"city", "town"} else "destination"


def _transport_role(place: dict) -> tuple[str, ...]:
    name = str(place.get("canonical", ""))
    roles: list[str] = []
    if name in AIR_HUB_NAMES or place.get("kind") == "airport":
        roles.append("air_hub")
    if name in RAIL_HUBS:
        roles.append("rail_hub")
    if name in CRUISE_PORTS:
        roles.append("cruise_port")
    if place.get("kind") in {"fjord", "route"}:
        roles.append("scenic_route")
    if place.get("kind") == "national_park":
        roles.append("nature_gateway")
    return tuple(roles or ("destination",))


def _priority(place: dict) -> int:
    name = str(place.get("canonical", ""))
    kind = str(place.get("kind", ""))
    if name in {"Oslo", "Bergen", "Stavanger", "Kristiansand", "Tromsø", "Trondheim", "Ålesund", "Flåm", "Geiranger", "Stockholm", "Gothenburg", "Malmö", "Kiruna", "Abisko", "Åre", "Visby", "Helsinki", "Rovaniemi", "Turku", "Tampere", "Levi", "Saariselkä", "Porvoo", "Åland", "Copenhagen", "Aarhus", "Odense", "Aalborg", "Billund", "Roskilde", "Helsingør", "Skagen", "Bornholm", "Reykjavík", "Keflavík", "Blue Lagoon", "Golden Circle", "South Coast", "Vík", "Jökulsárlón", "Skaftafell", "Vatnajökull", "Akureyri", "Mývatn", "Húsavík", "Snæfellsnes", "Ísafjörður", "Westfjords", "Landmannalaugar", "Ring Road"}:
        return 100
    if name in CRUISE_PORTS or name in RAIL_HUBS:
        return 85
    if kind in {"city", "town"}:
        return 70
    if kind in {"village", "resort", "fjord", "national_park", "island"}:
        return 60
    return 40


def _nearby_hubs(place: dict) -> tuple[str, ...]:
    country = str(place.get("country", ""))
    region = _region(place)
    if country == "Iceland":
        if region in {"Capital Region", "Reykjanes", "Golden Circle", "West Iceland"}:
            return ("Reykjavík", "Keflavík")
        if region in {"South Iceland", "South Coast and Islands", "Vatnajökull Region", "Southeast Iceland"}:
            return ("Reykjavík", "Vík", "Höfn")
        if region in {"Snæfellsnes", "Westfjords"}:
            return ("Reykjavík", "Ísafjörður", "Stykkishólmur")
        if region == "North Iceland":
            return ("Akureyri", "Húsavík")
        if region == "East Iceland":
            return ("Egilsstaðir", "Seyðisfjörður")
        if region == "Icelandic Highlands":
            return ("Reykjavík", "Akureyri")
        if region == "Iceland Ring Road":
            return ("Reykjavík", "Akureyri", "Höfn")
    if region in {"Sognefjord", "Hardanger", "Western Norway", "Nordfjord", "Sunnfjord"}:
        return ("Bergen",)
    if region in {"Southern Norway", "Rogaland"}:
        return ("Kristiansand", "Stavanger")
    if region in {"Lofoten", "Northern Norway"}:
        return ("Bodø", "Tromsø")
    if region == "Trøndelag":
        return ("Trondheim",)
    if region in {"Eastern Norway", "Oslofjord", "Vestfold and Telemark"}:
        return ("Oslo",)
    if region in {"Stockholm and Central Sweden", "Stockholm Archipelago", "Central Sweden", "Östergötland"}:
        return ("Stockholm",)
    if region in {"West Sweden", "Värmland"}:
        return ("Gothenburg",)
    if region == "Skåne":
        return ("Malmö", "Copenhagen")
    if region in {"Småland and Islands", "Gotland and Öland"}:
        return ("Stockholm", "Malmö")
    if region in {"Dalarna", "Gävleborg"}:
        return ("Stockholm",)
    if region in {"High Coast", "Jämtland Härjedalen"}:
        return ("Sundsvall", "Östersund")
    if region == "Swedish Lapland":
        return ("Luleå", "Kiruna")
    if region in {"Capital Region", "Southern Coast", "Southern Finland"}:
        return ("Helsinki",)
    if region in {"Southwest Finland", "Åland and Archipelago"}:
        return ("Turku", "Helsinki")
    if region in {"West Coast", "Ostrobothnia"}:
        return ("Vaasa", "Turku")
    if region in {"Finnish Lakeland", "North Karelia"}:
        return ("Tampere", "Kuopio")
    if region in {"Northern Ostrobothnia", "Kainuu"}:
        return ("Oulu", "Kajaani")
    if region == "Finnish Lapland":
        return ("Rovaniemi", "Kittilä", "Ivalo")
    if region in {"Greater Copenhagen", "North Zealand", "Zealand", "South Zealand and Islands"}:
        return ("Copenhagen", "Roskilde")
    if region == "Bornholm":
        return ("Copenhagen", "Rønne")
    if region in {"Funen and Islands", "Danish Islands"}:
        return ("Odense", "Copenhagen")
    if region in {"East Jutland", "South Jutland"}:
        return ("Aarhus", "Billund", "Copenhagen")
    if region == "West Jutland":
        return ("Billund", "Esbjerg")
    if region == "North Jutland":
        return ("Aalborg", "Aarhus")
    return ()


def destination_from_place(place: dict) -> NordicDestination:
    return NordicDestination(
        name=str(place.get("canonical", "")).strip(),
        country=str(place.get("country", "")).strip(),
        region=_region(place),
        destination_type=str(place.get("kind", "")).strip() or "destination",
        aliases=_aliases(place),
        nearby_hubs=_nearby_hubs(place),
        season_profile=_season_profile(place),
        image_profile=_image_profile(place),
        copy_profile=_copy_profile(place),
        transport_role=_transport_role(place),
        priority=_priority(place),
    )


@lru_cache(maxsize=1)
def registry_records() -> tuple[NordicDestination, ...]:
    return tuple(destination_from_place(place) for place in PLACES)


def travel_destination_records(records: Iterable[NordicDestination] | None = None) -> tuple[NordicDestination, ...]:
    source = tuple(records) if records is not None else registry_records()
    return tuple(record for record in source if record.destination_type in TRAVEL_DESTINATION_KINDS)


def _normalise(value: object) -> str:
    text = str(value or "").strip().lower()
    text = (
        text.replace("æ", "ae")
        .replace("ø", "o")
        .replace("å", "a")
        .replace("ä", "a")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ð", "d")
        .replace("þ", "th")
    )
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


@lru_cache(maxsize=1)
def alias_index() -> dict[str, NordicDestination]:
    index: dict[str, NordicDestination] = {}
    for record in registry_records():
        values = (record.name, *record.aliases)
        for value in values:
            key = _normalise(value)
            if key and key not in index:
                index[key] = record
    return index


def destination_for_alias(value: object) -> NordicDestination | None:
    return alias_index().get(_normalise(value))


def destination_country_for_alias(value: object) -> str:
    record = destination_for_alias(value)
    return record.country.lower() if record else ""


def registry_city_aliases() -> dict[str, set[str]]:
    aliases: dict[str, set[str]] = {}
    for record in registry_records():
        if record.destination_type not in TRAVEL_DESTINATION_KINDS:
            continue
        key = _normalise(record.name)
        if not key:
            continue
        aliases.setdefault(key, set()).add(record.name)
        aliases[key].update(record.aliases)
    return aliases


def is_southern_coastal_destination(value: object) -> bool:
    record = destination_for_alias(value)
    return bool(record and record.season_profile == "southern_coastal")
