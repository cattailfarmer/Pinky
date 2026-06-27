from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.irregular_primes import irregular_prime_distribution


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure irregular primes against whole-prime distribution rows.")
    parser.add_argument("--x", type=int, action="append", help="Sample point. May be repeated.")
    parser.add_argument("--max-x", type=int, default=200, help="Max generated sample point when --x is omitted.")
    parser.add_argument("--count", type=int, default=6, help="Generated sample count when --x is omitted.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision metadata.")
    parser.add_argument("--include-members", action="store_true", help="Include irregular primes up to each sample point.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = irregular_prime_distribution(
        points=args.x,
        max_x=args.max_x,
        count=args.count,
        dps=args.dps,
        include_members=args.include_members,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
