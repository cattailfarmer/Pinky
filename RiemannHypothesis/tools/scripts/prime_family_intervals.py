from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from rh_math.common import emit_payload
from rh_math.distribution import prime_family_interval_distribution
from rh_math.prime_families import special_prime_family_names


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure special-prime family increments inside whole-field intervals.")
    parser.add_argument("--x", type=int, action="append", help="Interval endpoint. May be repeated.")
    parser.add_argument("--max-x", type=int, default=100000, help="Max generated endpoint when --x is omitted.")
    parser.add_argument("--count", type=int, default=6, help="Generated endpoint count when --x is omitted.")
    parser.add_argument("--family", choices=special_prime_family_names(), action="append", help="Family to include. May be repeated.")
    parser.add_argument("--max-fermat-n", type=int, default=8, help="Largest Fermat number index to test divisibility against.")
    parser.add_argument("--dps", type=int, default=80, help="Decimal precision.")
    parser.add_argument("--include-members", action="store_true", help="Include family members in each interval.")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", help="Optional output file.")
    args = parser.parse_args()

    payload = prime_family_interval_distribution(
        points=args.x,
        max_x=args.max_x,
        count=args.count,
        families=args.family,
        max_fermat_n=args.max_fermat_n,
        dps=args.dps,
        include_members=args.include_members,
    )
    emit_payload(payload, args.format, args.output)


if __name__ == "__main__":
    main()
