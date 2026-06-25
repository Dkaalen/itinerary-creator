"""Declarative product-rule metadata and match value objects."""

from dataclasses import dataclass
from typing import Literal

ProductConfidence=Literal["strong","weak"]

@dataclass(frozen=True)
class ProductRule:
    rule_id:str;label:str;strong_title:str="";weak_title:str="";warning_code:str="";warning_message:str=""

@dataclass(frozen=True)
class ProductRuleMatch:
    rule_id:str;title:str="";confidence:ProductConfidence="strong";description:str="";warning_code:str="";warning_message:str=""
    @property
    def is_strong(self)->bool:return self.confidence=="strong"
    @property
    def is_weak(self)->bool:return self.confidence=="weak"

PRODUCT_RULES=(
 ProductRule("tallinn_old_town_guided_tour","Tallinn Old Town guided tour",strong_title="Old Town Guided Tour"),
 ProductRule("tallinn_ferry_framework","Helsinki–Tallinn ferry framework",strong_title="Day Excursion to Tallinn"),
 ProductRule("norway_in_a_nutshell","Norway in a Nutshell",strong_title="Norway in a Nutshell"),
 ProductRule("munch_museum","Munch Museum",strong_title="Munch Museum Visit"),
 ProductRule("fjellheisen","Fjellheisen Cable Car",strong_title="Fjellheisen Cable Car"),
 ProductRule("tromso_viewpoint_ticket_possible_fjellheisen","Possible Tromsø viewpoint ticket",weak_title="Round-trip viewpoint ticket in Tromsø",warning_code="ambiguous_activity_title",warning_message="Activity title came from a generic 'Round Trip Ticket' row in Tromsø; confirm the exact product name before final output."),
 ProductRule("santa_claus_friends","Santa Claus and friends",strong_title="Meet Santa Claus and his friends"),
 ProductRule("korouoma_canyon","Korouoma Canyon"),
)
RULE_BY_ID={rule.rule_id:rule for rule in PRODUCT_RULES}
