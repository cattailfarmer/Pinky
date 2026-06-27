from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.distribution import prime_power_decomposition


def main() -> None:
    parser = argparse.ArgumentParser(description="Decompose Chebyshev psi into prime-power layers.")
    parser.add_argument("--x", type=int, action="append", help="Sample point or interval endpoint. May be repeated.")
    parser.add_argument("--max-x", type=int, default=1000, help="Max generated endpoint when --x is omitted.")
    parser.add_argument("--count", type=int, default=6, help="Generated endpoint count when --x is omitted.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--include-events", action="store_true", help="Include individual prime-power events.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = prime_power_decomposition(
        points=args.x,
        max_x=args.max_x,
        count=args.count,
        dps=args.dps,
        include_events=args.include_events,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
