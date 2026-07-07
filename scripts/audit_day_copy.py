"""Print a compact day-brain copy audit for known weak itinerary shapes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from itinerary_generation.day_copy_audit import audit_day_copy_cases
from tests.fixtures.day_brain_cases import DAY_BRAIN_AUDIT_CASES


if __name__ == "__main__":
    print(json.dumps(audit_day_copy_cases(DAY_BRAIN_AUDIT_CASES), ensure_ascii=False, indent=2))
