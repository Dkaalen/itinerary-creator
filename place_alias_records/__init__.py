"""Country-scoped Nordic place alias records."""

from __future__ import annotations

from .denmark import DENMARK_PLACES
from .finland import FINLAND_PLACES
from .iceland import ICELAND_PLACES
from .norway import NORWAY_PLACES
from .service_phrases import SERVICE_PHRASES
from .sweden import SWEDEN_PLACES

PLACES = [
    *NORWAY_PLACES,
    *SWEDEN_PLACES,
    *FINLAND_PLACES,
    *ICELAND_PLACES,
    *DENMARK_PLACES,
]

__all__ = ["PLACES", "SERVICE_PHRASES"]
