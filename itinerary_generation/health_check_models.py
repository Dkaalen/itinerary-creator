"""Models and thresholds for itinerary health checks."""

from dataclasses import asdict, dataclass

CRITICAL = "critical"
REVIEW = "review"
INFO = "info"

CONTENT_TYPES = {"Activity", "Cruise", "Ferry", "Flight", "Hotel", "Rental Car", "Self Drive", "Train", "Transfer"}
TRANSFER_TYPES = {"Transfer", "Flight", "Train", "Ferry", "Cruise", "Rental Car", "Self Drive", "Transport"}
DAY_OVERFLOW_TEXT_LIMIT = 2600
DAY_OVERFLOW_SERVICE_LIMIT = 6
HEAVY_ACTIVITY_LIMIT = 4


@dataclass(frozen=True)
class ItineraryHealthIssue:
    code: str
    severity: str
    message: str
    day: str = ""
    city: str = ""
    row_type: str = ""
    source: str = "parsed_rows"

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ItineraryHealthSummary:
    critical: int
    review: int
    info: int
    total: int

    @property
    def status_label(self) -> str:
        if self.critical: return "Needs review"
        if self.review: return "Review"
        return "Clear"
