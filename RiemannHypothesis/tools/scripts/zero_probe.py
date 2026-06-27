from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.zeta import known_zero_probe


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe mpmath nontrivial zeta zero lookups and residuals.")
    parser.add_argument("--start", type=int, default=1, help="First zero index, 1-based.")
    parser.add_argument("--count", type=int, default=10, help="Number of zeros.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()
    emit_payload(known_zero_probe(args.start, args.count, args.dps), args.format, args.output)


if __name__ == "__main__":
    main()
