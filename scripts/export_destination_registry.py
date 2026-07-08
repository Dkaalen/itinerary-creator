"""Export the Nordic destination registry to JSON for review/diffing.

The production registry remains Python-owned for now.  This exporter is the safe
first step toward externalizing large static data: it creates a stable data file
that can be validated and reviewed before any runtime loader migration.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from itinerary_generation.destination_registry import registry_records


def destination_to_dict(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        data = asdict(value)
    elif isinstance(value, dict):
        data = dict(value)
    else:
        data = {name: getattr(value, name) for name in dir(value) if not name.startswith("_") and not callable(getattr(value, name))}
    return {key: list(item) if isinstance(item, tuple) else item for key, item in data.items()}


def build_registry_export() -> dict[str, Any]:
    destinations = [destination_to_dict(item) for item in registry_records()]
    return {
        "schema_version": 1,
        "destination_count": len(destinations),
        "destinations": sorted(destinations, key=lambda item: (str(item.get("country", "")), str(item.get("name", "")))),
    }


def validate_registry_export(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    names: set[str] = set()
    for index, item in enumerate(data.get("destinations", []) or [], start=1):
        name = str(item.get("name", "")).strip()
        country = str(item.get("country", "")).strip()
        if not name:
            errors.append(f"destination[{index}] missing name")
        if not country:
            errors.append(f"destination[{index}] missing country")
        key = f"{country.casefold()}::{name.casefold()}"
        if key in names:
            errors.append(f"duplicate destination record: {country} / {name}")
        names.add(key)
    if len(names) != int(data.get("destination_count", -1)):
        errors.append("destination_count does not match exported destination list")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/reports/static_data/destination_registry.json")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    data = build_registry_export()
    errors = validate_registry_export(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    if not args.validate_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {args.output}")
    print(f"destination registry export validated: {data['destination_count']} destinations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
