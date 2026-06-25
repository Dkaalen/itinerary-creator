"""Data models for Vipin Excel corpus runner."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ExcelCorpusItem:
    file: str
    sheet: str
    row: int
    day: str
    row_type: str
    city: str
    element: str
    nights: str = ""
    from_date: str = ""
    to_date: str = ""
    supplier: str = ""

    @property
    def source_id(self) -> str:
        return f"{self.file}::{self.sheet}::R{self.row}"

    def as_raw_line(self) -> str:
        values = [
            "",
            self.day,
            self.row_type,
            self.nights,
            self.from_date,
            self.to_date,
            "",
            "",
            self.supplier,
            self.city,
            self.element,
        ]
        return "\t".join(str(value or "") for value in values)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExcelCorpusItem":
        return cls(
            file=str(data.get("file", "") or ""),
            sheet=str(data.get("sheet", "") or ""),
            row=int(data.get("row", 0) or 0),
            day=str(data.get("day", "") or ""),
            row_type=str(data.get("row_type", "") or ""),
            city=str(data.get("city", "") or ""),
            element=str(data.get("element", "") or ""),
            nights=str(data.get("nights", "") or ""),
            from_date=str(data.get("from_date", "") or ""),
            to_date=str(data.get("to_date", "") or ""),
            supplier=str(data.get("supplier", "") or ""),
        )


@dataclass(frozen=True)
class BadOutput:
    source_id: str
    category: str
    reason: str
    source_type: str
    source_day: str
    source_city: str
    source_date: str
    parsed_type: str = ""
    effective_type: str = ""
    parsed_city: str = ""
    parsed_title: str = ""
    generated_title: str = ""
    confidence: int | None = None
    flags: tuple[str, ...] = ()
    details_excerpt: str = ""

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["flags"] = list(self.flags)
        return data
