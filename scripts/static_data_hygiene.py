"""Audit split static destination and alias data for cleanup readiness."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from place_alias_records import PLACES, SERVICE_PHRASES
from scripts.export_destination_registry import build_registry_export, validate_registry_export

DEFAULT_JSON = REPO_ROOT / "docs/reports/static_data/hygiene_latest.json"
DEFAULT_MD = REPO_ROOT / "docs/reports/static_data/hygiene_latest.md"

CURRENCY_CODES = {"DKK", "EUR", "GBP", "ISK", "NOK", "SEK", "USD"}
SERVICE_HINTS = ("transfer", "optional", "addon", "flybus", "hotel to", "airport to", "station to")
TRANSIT_KINDS = {"airport", "station", "port", "route"}


@dataclass(frozen=True)
class StaticDataSignal:
    code: str
    severity: str
    message: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class StaticDataHygieneReport:
    destination_count: int
    alias_record_count: int
    alias_value_count: int
    service_phrase_count: int
    registry_validation_errors: tuple[str, ...]
    signals: tuple[StaticDataSignal, ...]

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["signal_count"] = self.signal_count
        return data


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.casefold().split())


def _iter_names_and_aliases() -> Iterable[tuple[str, str, str]]:
    for place in PLACES:
        country = str(place.get("country", "")).strip()
        canonical = str(place.get("canonical", "")).strip()
        if canonical:
            yield country, canonical, canonical
        for alias in place.get("aliases", []) or []:
            alias_text = str(alias).strip()
            if alias_text:
                yield country, canonical, alias_text


def _duplicate_alias_signals() -> list[StaticDataSignal]:
    seen: dict[str, dict[str, set[str]]] = {}
    for country, canonical, value in _iter_names_and_aliases():
        key = _norm(value)
        record_key = f"{country}/{canonical}"
        seen.setdefault(key, {}).setdefault(record_key, set()).add(value)
    signals: list[StaticDataSignal] = []
    for key, records in sorted(seen.items()):
        if not key or len(records) <= 1:
            continue
        values = tuple(f"{record}: {', '.join(sorted(names))}" for record, names in sorted(records.items()))
        signals.append(
            StaticDataSignal(
                code="duplicate_alias_value",
                severity="review",
                message="Alias/canonical value appears in more than one place record.",
                values=values,
            )
        )
    return signals


def _service_phrase_overlap_signals() -> list[StaticDataSignal]:
    service_keys = {_norm(value): value for value in SERVICE_PHRASES}
    signals: list[StaticDataSignal] = []
    for country, canonical, value in _iter_names_and_aliases():
        key = _norm(value)
        if key in service_keys:
            signals.append(
                StaticDataSignal(
                    code="service_phrase_alias_overlap",
                    severity="risk",
                    message="Service phrase is also present as a place alias/canonical value.",
                    values=(f"{country}/{canonical}: {value}", service_keys[key]),
                )
            )
    return signals


def _currency_false_positive_signals() -> list[StaticDataSignal]:
    signals: list[StaticDataSignal] = []
    for country, canonical, value in _iter_names_and_aliases():
        if value.upper() in CURRENCY_CODES:
            signals.append(
                StaticDataSignal(
                    code="currency_code_alias",
                    severity="risk",
                    message="Currency code appears as a place alias/canonical value.",
                    values=(f"{country}/{canonical}: {value}",),
                )
            )
    return signals


def _service_like_destination_signals(destinations: list[dict]) -> list[StaticDataSignal]:
    signals: list[StaticDataSignal] = []
    for item in destinations:
        name = str(item.get("name", ""))
        aliases = [str(alias) for alias in item.get("aliases", []) or []]
        haystack = " ".join([name, *aliases]).casefold()
        if any(hint in haystack for hint in SERVICE_HINTS):
            signals.append(
                StaticDataSignal(
                    code="service_like_destination_name",
                    severity="review",
                    message="Destination record contains service/transfer wording; verify it is intentional.",
                    values=(str(item.get("country", "")), name, str(item.get("destination_type", ""))),
                )
            )
    return signals


def _transit_role_summary(destinations: list[dict]) -> StaticDataSignal:
    transit = [item for item in destinations if str(item.get("destination_type", "")).casefold() in TRANSIT_KINDS]
    airport_count = sum(1 for item in transit if str(item.get("destination_type", "")).casefold() == "airport")
    route_count = sum(1 for item in transit if str(item.get("destination_type", "")).casefold() == "route")
    return StaticDataSignal(
        code="transit_only_summary",
        severity="info",
        message="Transit/route records are intentionally present but should not become leisure destinations by default.",
        values=(f"transit_records={len(transit)}", f"airports={airport_count}", f"routes={route_count}"),
    )


def build_report() -> StaticDataHygieneReport:
    registry = build_registry_export()
    destinations = list(registry.get("destinations", []) or [])
    signals = [
        *_duplicate_alias_signals(),
        *_service_phrase_overlap_signals(),
        *_currency_false_positive_signals(),
        *_service_like_destination_signals(destinations),
        _transit_role_summary(destinations),
    ]
    alias_values = [value for _country, _canonical, value in _iter_names_and_aliases()]
    return StaticDataHygieneReport(
        destination_count=int(registry.get("destination_count", 0)),
        alias_record_count=len(PLACES),
        alias_value_count=len(alias_values),
        service_phrase_count=len(SERVICE_PHRASES),
        registry_validation_errors=tuple(validate_registry_export(registry)),
        signals=tuple(signals),
    )


def markdown_report(report: StaticDataHygieneReport) -> str:
    by_code: dict[str, int] = {}
    for signal in report.signals:
        by_code[signal.code] = by_code.get(signal.code, 0) + 1
    lines = [
        "# Static Data Hygiene Report",
        "",
        "Generated by `scripts/static_data_hygiene.py`.",
        "",
        f"Destination records: `{report.destination_count}`",
        f"Alias records: `{report.alias_record_count}`",
        f"Alias/canonical values: `{report.alias_value_count}`",
        f"Service phrases: `{report.service_phrase_count}`",
        f"Registry validation errors: `{len(report.registry_validation_errors)}`",
        f"Signals: `{report.signal_count}`",
        "",
        "## Signal counts",
    ]
    if by_code:
        lines.extend(f"- `{code}`: {count}" for code, count in sorted(by_code.items()))
    else:
        lines.append("- None detected")
    if report.registry_validation_errors:
        lines.extend(["", "## Registry validation errors"])
        lines.extend(f"- {error}" for error in report.registry_validation_errors)
    lines.extend(["", "## Review signals"])
    review_signals = [signal for signal in report.signals if signal.severity != "info"][:80]
    if review_signals:
        for signal in review_signals:
            lines.append(f"- `{signal.severity}` `{signal.code}` — {signal.message} :: {' | '.join(signal.values)}")
    else:
        lines.append("- None detected")
    lines.extend(["", "## Notes", "", "This report is cleanup guidance. Do not delete alias or destination records without fixture-backed parser/output tests."])
    return "\n".join(lines).rstrip() + "\n"


def write_report(report: StaticDataHygieneReport, *, json_path: Path = DEFAULT_JSON, md_path: Path = DEFAULT_MD) -> tuple[Path, Path]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit static destination and alias data hygiene.")
    parser.add_argument("--json-output", default=str(DEFAULT_JSON))
    parser.add_argument("--md-output", default=str(DEFAULT_MD))
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    if args.no_write:
        print(markdown_report(report), end="")
    else:
        json_path, md_path = write_report(report, json_path=Path(args.json_output), md_path=Path(args.md_output))
        print(f"Wrote {json_path}")
        print(f"Wrote {md_path}")
        print(f"signals={report.signal_count}")
    return 1 if report.registry_validation_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
